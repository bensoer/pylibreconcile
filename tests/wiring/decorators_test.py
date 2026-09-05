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
    observer = FakeObserver()

    @register_observed_state_handler(observer)
    class MyState(DesiredState):
        pass

    container = WiringContainer()
    result = container.get(MyState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None


def test_only_manager_decorator_registers_manager_only() -> None:
    manager = FakeManager()

    @register_resource_manager(manager)
    class MyState(DesiredState):
        pass

    container = WiringContainer()
    result = container.get(MyState)
    assert result is not None
    assert result[0] is None
    assert result[1] is manager


def test_both_decorators_register_both() -> None:
    observer = FakeObserver()
    manager = FakeManager()

    @register_resource_manager(manager)
    @register_observed_state_handler(observer)
    class MyState(DesiredState):
        pass

    container = WiringContainer()
    result = container.get(MyState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_decorator_order_does_not_matter() -> None:
    observer1 = FakeObserver()
    manager1 = FakeManager()
    observer2 = FakeObserver()
    manager2 = FakeManager()

    @register_observed_state_handler(observer1)
    @register_resource_manager(manager1)
    class MyState1(DesiredState):
        pass

    @register_resource_manager(manager2)
    @register_observed_state_handler(observer2)
    class MyState2(DesiredState):
        pass

    container = WiringContainer()
    result1 = container.get(MyState1)
    result2 = container.get(MyState2)

    assert result1 is not None
    assert result2 is not None
    assert result1[0] is observer1
    assert result1[1] is manager1
    assert result2[0] is observer2
    assert result2[1] is manager2


def test_undecorated_subclass_is_not_registered() -> None:
    class PlainState(DesiredState):
        pass

    container = WiringContainer()
    assert container.get(PlainState) is None


def test_decorator_returns_class_unchanged() -> None:
    @register_observed_state_handler(FakeObserver())
    class MyState(DesiredState):
        pass

    assert issubclass(MyState, DesiredState)
    instance = MyState()
    assert isinstance(instance, MyState)
    assert hasattr(MyState, "__dataclass_fields__")


def test_decorator_does_not_add_dataclass_fields() -> None:
    @dataclass
    class BaseState(DesiredState):
        field1: int = 0

    @register_observed_state_handler(FakeObserver())
    class DecoratedState(BaseState):
        field2: str = ""

    base_fields = {f.name for f in fields(BaseState)}
    decorated_fields = {f.name for f in fields(DecoratedState)}
    assert base_fields == {"field1"}
    assert decorated_fields == {"field1", "field2"}


@dataclass
class MyStateForDecoratorTest(DesiredState):
    field1: int = 0


def test_decorator_with_explicit_dataclass_still_works() -> None:
    observer = FakeObserver()
    decorated = register_observed_state_handler(observer)(MyStateForDecoratorTest)

    container = WiringContainer()
    result = container.get(decorated)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None


def test_decorator_with_inheritance_chain() -> None:
    observer = FakeObserver()

    @register_observed_state_handler(observer)
    class ParentState(DesiredState):
        pass

    class ChildState(ParentState):
        pass

    container = WiringContainer()
    result = container.get(ChildState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None


def test_decorator_does_not_mutate_class_dict() -> None:
    @register_observed_state_handler(FakeObserver())
    class MyState(DesiredState):
        pass

    assert "_observed_state_handler_instance" not in MyState.__dict__
    assert "_resource_manager_instance" not in MyState.__dict__


def test_end_to_end_both_decorators_with_fields() -> None:
    observer = FakeObserver()
    manager = FakeManager()

    @register_observed_state_handler(observer)
    @register_resource_manager(manager)
    class ServerDesired(DesiredState):
        hostname: str
        port: int

    container = WiringContainer()
    result = container.get(ServerDesired)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager

    instance = ServerDesired(hostname="a", port=80)
    assert instance.hostname == "a"
    assert instance.port == 80
    assert hasattr(ServerDesired, "__dataclass_fields__")


def test_end_to_end_inherits_via_mro() -> None:
    observer = FakeObserver()

    @register_observed_state_handler(observer)
    class Parent(DesiredState):
        name: str

    class Child(Parent):
        pass

    container = WiringContainer()
    result = container.get(Child)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None
