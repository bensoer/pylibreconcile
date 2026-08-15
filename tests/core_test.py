"""Tests for the core module."""

from dataclasses import asdict, astuple, dataclass, field, fields, is_dataclass, replace

from pylibreconcile import DesiredState


def test_desired_state_to_hash() -> None:
    """Verify DesiredState creates a hash from its attributes."""

    class ExampleState(DesiredState):
        id: int
        name: str

    state = ExampleState(id=1, name="test")
    assert isinstance(state.to_hash(), int)


def test_desired_state_subclass_is_dataclass() -> None:
    """Verify subclasses of DesiredState are automatically converted to dataclasses."""

    class ExampleState(DesiredState):
        id: int
        name: str

    instance = ExampleState(id=1, name="test")
    assert instance.id == 1
    assert instance.name == "test"


def test_desired_state_subclass_has_init() -> None:
    """Verify subclasses have auto-generated __init__ from dataclass decorator."""

    class ExampleState(DesiredState):
        id: int
        name: str

    instance = ExampleState(42, "auto")
    assert instance.id == 42
    assert instance.name == "auto"


def test_desired_state_subclass_has_repr() -> None:
    """Verify subclasses have auto-generated __repr__ from dataclass decorator."""

    class ExampleState(DesiredState):
        id: int
        name: str

    instance = ExampleState(id=1, name="test")
    repr_str = repr(instance)
    assert "ExampleState" in repr_str
    assert "id=1" in repr_str
    assert "name='test'" in repr_str


def test_desired_state_subclass_has_eq() -> None:
    """Verify subclasses have auto-generated __eq__ from dataclass decorator."""

    class ExampleState(DesiredState):
        id: int
        name: str

    instance1 = ExampleState(id=1, name="test")
    instance2 = ExampleState(id=1, name="test")
    instance3 = ExampleState(id=2, name="other")
    assert instance1 == instance2
    assert instance1 != instance3


def test_desired_state_to_hash_consistency() -> None:
    """Verify hash is consistent across instances with same field values."""

    class ExampleState(DesiredState):
        id: int
        name: str

    instance1 = ExampleState(id=1, name="test")
    instance2 = ExampleState(id=1, name="test")
    assert instance1.to_hash() == instance2.to_hash()


def test_desired_state_to_hash_changes_with_values() -> None:
    """Verify hash changes when field values change."""

    class ExampleState(DesiredState):
        id: int
        name: str

    instance1 = ExampleState(id=1, name="test")
    instance2 = ExampleState(id=2, name="test")
    instance3 = ExampleState(id=1, name="other")
    assert instance1.to_hash() != instance2.to_hash()
    assert instance1.to_hash() != instance3.to_hash()


def test_desired_state_is_dataclass() -> None:
    """Verify subclasses are recognized as dataclasses by the dataclasses module."""

    class ExampleState(DesiredState):
        id: int
        name: str

    assert is_dataclass(ExampleState)


def test_desired_state_with_explicit_dataclass() -> None:
    """Verify a subclass explicitly decorated with @dataclass still works."""

    @dataclass
    class ExampleState(DesiredState):
        id: int
        name: str

    state = ExampleState(id=1, name="test")
    assert is_dataclass(ExampleState)
    assert [f.name for f in fields(ExampleState)] == ["id", "name"]
    assert state == ExampleState(id=1, name="test")
    assert asdict(state) == {"id": 1, "name": "test"}
    assert state.to_hash() == ExampleState(id=1, name="test").to_hash()


def test_desired_state_dataclass_fields() -> None:
    """Verify the dataclass fields match the declared annotations."""

    class ExampleState(DesiredState):
        id: int
        name: str

    field_names = [f.name for f in fields(ExampleState)]
    assert field_names == ["id", "name"]

    id_field = fields(ExampleState)[0]
    assert id_field.type is int


def test_desired_state_dataclass_default_values() -> None:
    """Verify dataclass default values and default_factory are honored."""

    class ExampleState(DesiredState):
        id: int
        name: str = "default"
        tags: list = field(default_factory=list)

    state = ExampleState(id=1)
    assert state.name == "default"
    assert state.tags == []


def test_desired_state_dataclass_field_order() -> None:
    """Verify dataclass fields preserve declaration order."""

    class ExampleState(DesiredState):
        z: int
        a: int
        m: int

    state = ExampleState(z=1, a=2, m=3)
    assert [f.name for f in fields(ExampleState)] == ["z", "a", "m"]
    assert astuple(state) == (1, 2, 3)


def test_desired_state_asdict() -> None:
    """Verify dataclasses.asdict works on subclasses."""

    class ExampleState(DesiredState):
        id: int
        name: str

    state = ExampleState(id=1, name="test")
    assert asdict(state) == {"id": 1, "name": "test"}


def test_desired_state_astuple() -> None:
    """Verify dataclasses.astuple works on subclasses."""

    class ExampleState(DesiredState):
        id: int
        name: str

    state = ExampleState(id=1, name="test")
    assert astuple(state) == (1, "test")


def test_desired_state_replace() -> None:
    """Verify dataclasses.replace creates a new instance with updated fields."""

    class ExampleState(DesiredState):
        id: int
        name: str

    state = ExampleState(id=1, name="test")
    replaced = replace(state, name="updated")
    assert replaced == ExampleState(id=1, name="updated")
    assert state == ExampleState(id=1, name="test")


def test_desired_state_field_options() -> None:
    """Verify dataclass field options (repr, compare, init) are respected."""

    class ExampleState(DesiredState):
        id: int
        hidden: str = field(repr=False, compare=False)
        computed: int = field(init=False, repr=False)

        def __post_init__(self) -> None:
            self.computed = self.id * 2

    state = ExampleState(id=2, hidden="value")
    assert "hidden" not in repr(state)
    assert "computed" not in repr(state)
    assert state.computed == 4

    same_id_different_hidden = ExampleState(id=2, hidden="other")
    assert state == same_id_different_hidden


def test_desired_state_classvar_excluded_from_fields() -> None:
    """Verify ClassVar annotations are not turned into dataclass fields."""

    from typing import ClassVar

    class ExampleState(DesiredState):
        id: int
        counter: ClassVar[int] = 0

    field_names = [f.name for f in fields(ExampleState)]
    assert field_names == ["id"]
    assert "counter" not in field_names


def test_desired_state_multi_level_inheritance() -> None:
    """Verify subclasses of subclasses also become full dataclasses."""

    class BaseState(DesiredState):
        id: int

    class ChildState(BaseState):
        name: str

    instance = ChildState(id=1, name="test")
    assert is_dataclass(ChildState)
    assert [f.name for f in fields(ChildState)] == ["id", "name"]
    assert instance.id == 1
    assert instance.name == "test"
    assert instance == ChildState(id=1, name="test")
    assert instance.to_hash() == ChildState(id=1, name="test").to_hash()


def test_desired_state_deep_inheritance() -> None:
    """Verify dataclass transformation works across three levels of inheritance."""

    class Level1(DesiredState):
        a: int

    class Level2(Level1):
        b: int

    class Level3(Level2):
        c: int

    instance = Level3(a=1, b=2, c=3)
    assert [f.name for f in fields(Level3)] == ["a", "b", "c"]
    assert instance == Level3(a=1, b=2, c=3)
    assert instance.to_hash() == Level3(a=1, b=2, c=3).to_hash()


def test_desired_state_five_level_inheritance() -> None:
    """Verify dataclass transformation works across five levels of inheritance."""

    class Level1(DesiredState):
        a: int

    class Level2(Level1):
        b: int

    class Level3(Level2):
        c: int

    class Level4(Level3):
        d: int

    class Level5(Level4):
        e: int

    instance = Level5(a=1, b=2, c=3, d=4, e=5)
    assert [f.name for f in fields(Level5)] == ["a", "b", "c", "d", "e"]
    assert instance == Level5(a=1, b=2, c=3, d=4, e=5)
    assert instance.to_hash() == Level5(a=1, b=2, c=3, d=4, e=5).to_hash()
    assert instance.e == 5


def test_desired_state_intermediate_explicit_dataclass() -> None:
    """Verify @dataclass on an intermediate level still allows further subclassing."""

    @dataclass
    class BaseState(DesiredState):
        id: int

    class ChildState(BaseState):
        name: str

    instance = ChildState(id=1, name="test")
    assert [f.name for f in fields(ChildState)] == ["id", "name"]
    assert instance == ChildState(id=1, name="test")
    assert instance.id == 1
    assert instance.name == "test"


def test_desired_state_cooperative_init_subclass() -> None:
    """Verify super().__init_subclass__() cooperates with sibling base classes."""

    calls: list[str] = []

    class Tracker:
        def __init_subclass__(cls, **kwargs: object) -> None:
            calls.append(cls.__name__)
            super().__init_subclass__(**kwargs)

    class ExampleState(Tracker, DesiredState):
        id: int

    assert calls == ["ExampleState"]
    assert is_dataclass(ExampleState)
    assert ExampleState(id=1).id == 1


def test_desired_state_to_hash_includes_compare_false_fields() -> None:
    """Verify to_hash covers all fields, even those excluded from __eq__."""

    class ExampleState(DesiredState):
        id: int
        hidden: str = field(compare=False)

    same_id_different_hidden = ExampleState(id=1, hidden="other")
    instance = ExampleState(id=1, hidden="value")
    assert instance == same_id_different_hidden
    assert instance.to_hash() != same_id_different_hidden.to_hash()


def test_desired_state_to_hash_includes_inherited_fields() -> None:
    """Verify to_hash includes fields inherited from parent classes."""

    class BaseState(DesiredState):
        id: int

    class ChildState(BaseState):
        name: str

    instance = ChildState(id=1, name="same")
    different_id = ChildState(id=2, name="same")
    assert instance.to_hash() != different_id.to_hash()


def test_desired_state_to_hash_matches_tuple_hash() -> None:
    """Verify to_hash equals the hash of the ordered field-value tuple."""

    class ExampleState(DesiredState):
        id: int
        name: str

    state = ExampleState(id=1, name="test")
    assert state.to_hash() == hash((1, "test"))
