from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from tests._compat import ensure_fastapi, ensure_jwt

ensure_fastapi()
ensure_jwt()

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.auth import AuthenticatedAthlete, _athlete_id_from_claims, require_authenticated_athlete
from app.schemas import ChatRequest, IntelligenceRequest, MAX_CHAT_MESSAGE_CHARACTERS, RequestValidationError


class AuthAndSchemaTests(unittest.IsolatedAsyncioTestCase):
    def test_chat_request_accepts_legacy_content_and_trims_whitespace(self) -> None:
        request = ChatRequest(content="  Show my recovery trend  ", timezone=" UTC ")

        self.assertEqual(request.text, "Show my recovery trend")
        self.assertEqual(request.timezone, "UTC")

    def test_chat_request_rejects_unknown_fields(self) -> None:
        with self.assertRaises(RequestValidationError):
            ChatRequest(content="Hello", unexpected="value")  # type: ignore[call-arg]

    def test_chat_request_rejects_blank_or_too_long_messages(self) -> None:
        with self.assertRaises(RequestValidationError):
            ChatRequest(content="   ")

        with self.assertRaises(RequestValidationError):
            ChatRequest(content="x" * (MAX_CHAT_MESSAGE_CHARACTERS + 1))

    def test_intelligence_request_strips_and_bounds_content(self) -> None:
        request = IntelligenceRequest(content="  Evaluate readiness  ")
        self.assertEqual(request.content, "Evaluate readiness")

        with self.assertRaises(RequestValidationError):
            IntelligenceRequest(content="   ")

    def test_chat_request_rejects_both_message_fields_and_missing_message(self) -> None:
        with self.assertRaises(RequestValidationError):
            ChatRequest(message="Hello", content="World")

        with self.assertRaises(RequestValidationError):
            ChatRequest()

    def test_chat_request_rejects_invalid_timezone_text(self) -> None:
        with self.assertRaises(RequestValidationError):
            ChatRequest(content="Hello", timezone=" " * 2)

        with self.assertRaises(RequestValidationError):
            ChatRequest(content="Hello", timezone="x" * 65)

    def test_athlete_id_must_be_positive_integer(self) -> None:
        self.assertEqual(_athlete_id_from_claims({"sub": "42"}), 42)
        for bad_sub in (0, -1, "0", "abc", True, None):
            with self.subTest(bad_sub=bad_sub):
                with self.assertRaises(ValueError):
                    _athlete_id_from_claims({"sub": bad_sub})

    async def test_authentication_rejects_missing_configuration(self) -> None:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as error:
                await require_authenticated_athlete(credentials)
        self.assertEqual(error.exception.status_code, 503)

    async def test_authentication_requires_bearer_token_challenge(self) -> None:
        with self.assertRaises(HTTPException) as error:
            await require_authenticated_athlete(None)
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.headers, {"WWW-Authenticate": "Bearer"})

    async def test_authentication_requires_valid_bearer_token(self) -> None:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "secret"}), patch("app.auth.jwt.decode", side_effect=ValueError("bad token")):
            with self.assertRaises(HTTPException) as error:
                await require_authenticated_athlete(credentials)
        self.assertEqual(error.exception.status_code, 401)

    async def test_authentication_returns_authenticated_athlete_for_valid_token(self) -> None:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "secret"}), patch(
            "app.auth.jwt.decode", return_value={"sub": "42", "exp": 1234567890}
        ):
            actor = await require_authenticated_athlete(credentials)
        self.assertEqual(actor, AuthenticatedAthlete(athlete_id=42))
