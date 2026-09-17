"""Minimal local compatibility layer for the request-schema tests.

This project only needs a very small slice of Pydantic behavior:

- `BaseModel` with `extra="forbid"`
- `Field(...)` defaults and metadata for `gt`
- `StrictInt` and `StrictStr`
- `field_validator` / `model_validator`
- a `ValidationError` type

The implementation below is intentionally narrow and only supports the
contracts used by `app.schemas`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, ClassVar, get_args, get_origin, get_type_hints


class ValidationError(ValueError):
    pass


class ConfigDict(dict):
    pass


StrictInt = int
StrictStr = str


@dataclass(frozen=True)
class FieldInfo:
    default: Any = ...
    description: str | None = None
    gt: int | None = None


def Field(default: Any = ..., **kwargs: Any) -> FieldInfo:
    return FieldInfo(default=default, description=kwargs.get("description"), gt=kwargs.get("gt"))


def field_validator(*field_names: str, mode: str | None = None):
    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        target = function.__func__ if isinstance(function, classmethod) else function
        setattr(target, "__pydantic_field_validator__", {"fields": field_names, "mode": mode})
        return function

    return decorator


def model_validator(*, mode: str):
    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        target = function.__func__ if isinstance(function, classmethod) else function
        setattr(target, "__pydantic_model_validator__", {"mode": mode})
        return function

    return decorator


class BaseModelMeta(type):
    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]):
        cls = super().__new__(mcls, name, bases, namespace)
        cls.__field_validators__ = []
        cls.__model_validators__ = []
        for base in reversed(bases):
            cls.__field_validators__.extend(getattr(base, "__field_validators__", []))
            cls.__model_validators__.extend(getattr(base, "__model_validators__", []))
        for attr_name, value in namespace.items():
            target = value.__func__ if isinstance(value, classmethod) else value
            info = getattr(target, "__pydantic_field_validator__", None)
            if info:
                cls.__field_validators__.append((attr_name, info))
            model_info = getattr(target, "__pydantic_model_validator__", None)
            if model_info:
                cls.__model_validators__.append((attr_name, model_info))
        return cls


class BaseModel(metaclass=BaseModelMeta):
    model_config: ClassVar[dict[str, Any]] = {}

    def __init__(self, **data: Any) -> None:
        annotations = get_type_hints(self.__class__, include_extras=True)
        field_names = self._field_names(annotations)
        if self._config().get("extra") == "forbid":
            self._reject_extra_fields(data, field_names)

        for field_name in field_names:
            annotation = annotations[field_name]
            value = self._resolve_field_value(field_name, data)
            setattr(self, field_name, self._validate_field(field_name, annotation, value))

        self._run_model_validators()

    def _config(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        for base in reversed(self.__class__.__mro__):
            config.update(getattr(base, "model_config", {}) or {})
        return config

    @staticmethod
    def _field_names(annotations: dict[str, Any]) -> list[str]:
        return [name for name in annotations if name != "model_config"]

    @staticmethod
    def _reject_extra_fields(data: dict[str, Any], field_names: list[str]) -> None:
        extra = set(data) - set(field_names)
        if extra:
            raise ValidationError(f"extra fields not permitted: {sorted(extra)!r}")

    def _resolve_field_value(self, field_name: str, data: dict[str, Any]) -> Any:
        raw_value = data.get(field_name, getattr(self.__class__, field_name, ...))
        if isinstance(raw_value, FieldInfo):
            raw_value = raw_value.default
        if raw_value is ...:
            raise ValidationError(f"field required: {field_name}")
        return raw_value

    def _validate_field(self, field_name: str, annotation: Any, value: Any) -> Any:
        try:
            value = self._validate_type(field_name, annotation, value)
            return self._apply_field_validators(field_name, value)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def _run_model_validators(self) -> None:
        for attr_name, info in self.__class__.__model_validators__:
            if info["mode"] != "after":
                continue
            try:
                getattr(self, attr_name)()
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

    @classmethod
    def _validate_type(cls, field_name: str, annotation: Any, value: Any) -> Any:
        if value is None:
            origin = get_origin(annotation)
            if origin is None:
                if annotation not in (Any, object) and annotation is not None:
                    raise ValidationError(f"{field_name} may not be None")
                return value
            if type(None) in get_args(annotation):
                return value
            raise ValidationError(f"{field_name} may not be None")

        origin = get_origin(annotation)
        options = get_args(annotation) if origin is not None else (annotation,)
        strict_types = tuple(option for option in options if option in (int, str))
        if strict_types and not isinstance(value, strict_types):
            raise ValidationError(f"invalid type for {field_name}")
        if int in options and isinstance(value, bool):
            raise ValidationError(f"invalid type for {field_name}")

        if isinstance(getattr(cls, field_name, None), FieldInfo):
            field_info = getattr(cls, field_name)
            if field_info.gt is not None and not (value > field_info.gt):
                raise ValidationError(f"{field_name} must be greater than {field_info.gt}")
        return value

    def _apply_field_validators(self, field_name: str, value: Any) -> Any:
        for attr_name, info in self.__class__.__field_validators__:
            if field_name not in info["fields"]:
                continue
            value = getattr(self.__class__, attr_name)(value)
        return value


__all__ = [
    "BaseModel",
    "ConfigDict",
    "Field",
    "FieldInfo",
    "StrictInt",
    "StrictStr",
    "ValidationError",
    "field_validator",
    "model_validator",
]
