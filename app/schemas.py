"""Typed, size-bounded request contracts for the public RhythmX API."""

from __future__ import annotations

MAX_CHAT_MESSAGE_CHARACTERS = 4_000
MAX_INTELLIGENCE_CONTENT_CHARACTERS = 12_000


class RequestValidationError(ValueError):
    """Raised when a public request does not meet its documented contract."""


class ChatRequest:
    """A chat request whose athlete identity is derived from a verified JWT."""

    def __init__(
        self,
        *,
        athlete_id: int | None = None,
        message: str | None = None,
        content: str | None = None,
        timezone: str = "UTC",
        **extra: object,
    ) -> None:
        if extra:
            raise RequestValidationError(f"extra fields not permitted: {sorted(extra)!r}")
        if athlete_id is not None and (type(athlete_id) is not int or athlete_id <= 0):
            raise RequestValidationError("athlete_id must be a positive integer")
        self.athlete_id = athlete_id
        self.message = self._validate_message(message)
        self.content = self._validate_message(content)
        self.timezone = self._validate_timezone(timezone)
        if self.message is None and self.content is None:
            raise RequestValidationError("message is required")
        if self.message is not None and self.content is not None:
            raise RequestValidationError("provide either message or content, not both")

    @staticmethod
    def _validate_message(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise RequestValidationError("message must be a string")
        cleaned = value.strip()
        if not cleaned:
            raise RequestValidationError("message must not be blank")
        if len(cleaned) > MAX_CHAT_MESSAGE_CHARACTERS:
            raise RequestValidationError(f"message must not exceed {MAX_CHAT_MESSAGE_CHARACTERS} characters")
        return cleaned

    @staticmethod
    def _validate_timezone(value: str) -> str:
        if not isinstance(value, str):
            raise RequestValidationError("timezone must be a string")
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 64:
            raise RequestValidationError("timezone must be a non-empty IANA timezone name")
        return cleaned

    @property
    def text(self) -> str:
        return self.message if self.message is not None else self.content or ""


class IntelligenceRequest:
    """A bounded, explicit specialist-model input payload."""

    def __init__(self, *, content: str, **extra: object) -> None:
        if extra:
            raise RequestValidationError(f"extra fields not permitted: {sorted(extra)!r}")
        if not isinstance(content, str):
            raise RequestValidationError("content must be a string")
        cleaned = content.strip()
        if not cleaned:
            raise RequestValidationError("content must not be blank")
        if len(cleaned) > MAX_INTELLIGENCE_CONTENT_CHARACTERS:
            raise RequestValidationError(f"content must not exceed {MAX_INTELLIGENCE_CONTENT_CHARACTERS} characters")
        self.content = cleaned
