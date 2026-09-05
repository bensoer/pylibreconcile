from __future__ import annotations

from dataclasses import dataclass, fields

from pylibreconcile import DesiredState, WiringContainer
from pylibreconcile.wiring.decorators import (
    register_observed_state_handler,
    register_resource_manager,
)


class FakeObserver:
    def exists(self, desired_state: DesiredState) -> bool:
        return True

    def is_match(self, desired_state: DesiredState) -> bool:
        return True


class FakeManager:
    def create(self, desired_state: DesiredState) -> None:
        pass

    def update(self, desired_state: DesiredState) -> None:
        pass

    def delete(self, desired_state: DesiredState) -> None:
        pass


def test_only_observer_decorator_registers_observer_only() -> None:
    @register_observed_state_handler(FakeObserver())
    class MyState(DesiredState):
        pass

    container = WiringContainer()
    result = container.get(MyState)
    assert result is not None
    assert isinstance(result[0], FakeObserver)
    assert result[1] is None


def test_only_manager_decorator_registers_manager_only() -> None:
    @register_resource_manager(FakeManager())
    class MyState(DesiredState):
        pass

    container = WiringContainer()
    result = container.get(MyState)
    assert result is not None
    assert result[0] is None
    assert isinstance(result[1], FakeManager)


def test_both_decorators_register_both() -> None:
    @register_resource_manager(FakeManager())
    @register_observed_state_handler(FakeObserver())
    class MyState(DesiredState):
        pass

    container = WiringContainer()
    result = container.get(MyState)
    assert result is not None
    assert isinstance(result[0], FakeObserver)
    assert isinstance(result[1], FakeManager)


def test_decorator_order_does_not_matter() -> None:
    # Order 1: observer then manager
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class MyState1(DesiredState):
        pass

    # Order 2: manager then observer
    @register_resource_manager(FakeManager())
    @register_observed_state_handler(FakeObserver())
    class MyState2(DesiredState):
        pass

    container = WiringContainer()
    result1 = container.get(MyState1)
    result2 = container.get(MyState2)

    assert result1 is not None
    assert result2 is not None
    assert isinstance(result1[0], FakeObserver)
    assert isinstance(result1[1], FakeManager)
    assert isinstance(result2[0], FakeObserver)
    assert isinstance(result2[1], FakeManager)


def test_undecorated_subclass_is_not_registered() -> None:
    class PlainState(DesiredState):
        pass

    container = WiringContainer()
    assert container.get(PlainState) is None


def test_decorator_returns_class_unchanged() -> None:
    original_state = DesiredState

    @register_observed_state_handler(FakeObserver())
    class MyState(DesiredState):
        pass

    assert MyState is not original_state
    # But it is still a subclass of DesiredState
    assert issubclass(MyState, DesiredState)
    # And it is still instantiable
    instance = MyState()
    assert isinstance(instance, MyState)
    # And it is still a dataclass (since DesiredState makes it one)
    assert hasattr(MyState, "__dataclass_fields__")


def test_decorator_does_not_add_dataclass_fields() -> None:
    @dataclass
    class BaseState(DesiredState):
        field1: int = 0

    @register_observed_state_handler(FakeObserver())
    class DecoratedState(BaseState):
        field2: str = ""

    # The decorated class should have the same fields as the base plus its own
    base_fields = {f.name for f in fields(BaseState)}
    decorated_fields = {f.name for f in fields(DecoratedState)}
    assert base_fields == {"field1"}
    assert decorated_fields == {"field1", "field2"}


@dataclass
class MyStateForDecoratorTest(DesiredState):
    field1: int = 0


def test_decorator_with_explicit_dataclass_still_works() -> None:
    decorated = register_observed_state_handler(FakeObserver())(MyStateForDecoratorTest)

    container = WiringContainer()
    result = container.get(decorated)
    assert result is not None
    assert isinstance(result[0], FakeObserver)
    assert result[1] is None


def test_decorator_with_inheritance_chain() -> None:
    @register_observed_state_handler(FakeObserver())
    class ParentState(DesiredState):
        pass

    class ChildState(ParentState):
        pass  # Not decorated

    container = WiringContainer()
    result = container.get(ChildState)
    assert result is not None
    assert isinstance(result[0], FakeObserver)
    assert result[1] is None


def test_decorator_does_not_mutate_class_dict() -> None:
    @register_observed_state_handler(FakeObserver())
    class MyState(DesiredState):
        pass

    # The class dict should not have any attributes added by the decorator
    # that are related to the wiring (like _observed_state_handler_instance)
    # We can check for common attribute names that the decorator might add.
    assert not hasattr(MyState, "_observed_state_handler_instance")
    assert not hasattr(MyState, "_resource_manager_instance")

    # Also, the class dict should not have any new attributes that start with _
    # that are related to our decorator (but we don't want to be too strict)
    # Instead, we can check that the class dict is the same as a non-decorated
    # class in terms of wiring-related attributes.
    class PlainState(DesiredState):
        pass

    # The only difference should be that MyState is not PlainState (different identity)
    # and that MyState has been decorated (but we don't have an easy way to check that
    # without knowing the internal implementation). However, we can check that
    # the decorator did not add any attributes that we know it shouldn't.
    # Since we don't know the exact internal, we can at least check for the two
    # attributes that we know the decorator might be tempted to add (but shouldn't).
    assert "_observed_state_handler_instance" not in MyState.__dict__
    assert "_resource_manager_instance" not in MyState.__dict__
