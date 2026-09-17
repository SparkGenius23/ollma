"""Typed, size-bounded request contracts for the public RhythmX API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator


MAX_CHAT_MESSAGE_CHARACTERS = 4_000
MAX_INTELLIGENCE_CONTENT_CHARACTERS = 12_000


class _StrictRequest(BaseModel):
    """Reject unknown fields so data sent to the model is intentional and documented."""

    model_config = ConfigDict(extra="forbid")


class ChatRequest(_StrictRequest):
    """A chat request whose athlete identity is derived from a verified JWT."""

    athlete_id: StrictInt | None = Field(
        default=None,
        gt=0,
        description="Optional migration field. When supplied, it must match the authenticated JWT subject.",
    )
    message: StrictStr | None = Field(default=None, description="Athlete question.")
    content: StrictStr | None = Field(default=None, description="Legacy alias for message.")
    timezone: StrictStr = Field(default="UTC", description="IANA timezone used to resolve relative dates.")

    @field_validator("message", "content")
    @classmethod
    def validate_message(cls, value: StrictStr | None) -> StrictStr | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be blank")
        if len(cleaned) > MAX_CHAT_MESSAGE_CHARACTERS:
            raise ValueError(f"message must not exceed {MAX_CHAT_MESSAGE_CHARACTERS} characters")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def validate_timezone_text(cls, value: StrictStr) -> StrictStr:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 64:
            raise ValueError("timezone must be a non-empty IANA timezone name")
        return cleaned

    @model_validator(mode="after")
    def require_one_message_field(self) -> "ChatRequest":
        if self.message is None and self.content is None:
            raise ValueError("message is required")
        if self.message is not None and self.content is not None:
            raise ValueError("provide either message or content, not both")
        return self

    @property
    def text(self) -> str:
        return self.message if self.message is not None else self.content or ""


class IntelligenceRequest(_StrictRequest):
    """A bounded, explicit specialist-model input payload."""

    content: StrictStr = Field(description="Pre-computed, domain-specific context for a specialist model.")

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: StrictStr) -> StrictStr:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be blank")
        if len(cleaned) > MAX_INTELLIGENCE_CONTENT_CHARACTERS:
            raise ValueError(f"content must not exceed {MAX_INTELLIGENCE_CONTENT_CHARACTERS} characters")
        return cleaned
