from __future__ import annotations

from dataclasses import dataclass, fields


class DesiredState:
    def __init_subclass__(cls: type[DesiredState], /, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "__dataclass_fields__" not in cls.__dict__:
            dataclass(cls)

    def to_hash(self) -> int:
        field_names = tuple(f.name for f in fields(self.__class__))  # type: ignore
        field_values = tuple(getattr(self, name) for name in field_names)
        return hash(field_values)
