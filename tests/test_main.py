import importlib.util
import logging
import logging.handlers
import sys
import types
import unittest
from unittest.mock import patch


def _install_runtime_stubs() -> None:
    """Allow request-routing unit tests to run without optional app packages."""
    if importlib.util.find_spec("asyncpg") is None:
        asyncpg = types.ModuleType("asyncpg")
        asyncpg.Pool = object
        asyncpg.PostgresError = Exception
        sys.modules["asyncpg"] = asyncpg
    if importlib.util.find_spec("dotenv") is None:
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *_args, **_kwargs: False
        sys.modules["dotenv"] = dotenv
    if importlib.util.find_spec("ollama") is None:
        ollama = types.ModuleType("ollama")
        ollama.AsyncClient = object
        sys.modules["ollama"] = ollama
    if importlib.util.find_spec("fastapi") is None:
        fastapi = types.ModuleType("fastapi")

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str) -> None:
                self.status_code = status_code
                self.detail = detail

        class FastAPI:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                self.state = types.SimpleNamespace()

            @staticmethod
            def _route(*_args: object, **_kwargs: object):
                return lambda function: function

            on_event = _route
            get = _route
            post = _route

        fastapi.BackgroundTasks = object
        fastapi.FastAPI = FastAPI
        fastapi.HTTPException = HTTPException
        fastapi.Request = object
        fastapi.status = types.SimpleNamespace(
            HTTP_404_NOT_FOUND=404,
            HTTP_422_UNPROCESSABLE_ENTITY=422,
            HTTP_503_SERVICE_UNAVAILABLE=503,
        )
        responses = types.ModuleType("fastapi.responses")
        responses.StreamingResponse = object
        sys.modules["fastapi"] = fastapi
        sys.modules["fastapi.responses"] = responses


_install_runtime_stubs()

# main.py configures a file handler at import time. Keep unit-test logs out of
# the tracked runtime log while preserving the application's normal behavior.
logging.handlers.RotatingFileHandler = lambda *_args, **_kwargs: logging.NullHandler()
import main


class FakeRequest:
    def __init__(self, body: object) -> None:
        self.body = body

    async def json(self) -> object:
        return self.body


class FakeTrendService:
    calls: list[tuple[object, int, object, object, object]] = []

    def __init__(self, pool: object) -> None:
        self.pool = pool

    async def build_payload(self, athlete_id: int, intent: object, start_date: object, end_date: object) -> dict[str, object]:
        self.calls.append((self.pool, athlete_id, intent, start_date, end_date))
        return {"metric": "sleep_score", "summary": {"trend": "increasing"}}


class MainRequestTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeTrendService.calls.clear()
        main.app.state.db_pool = None

    def test_athlete_id_accepts_numeric_string(self) -> None:
        self.assertEqual(main._athlete_id_from_body("42"), 42)

    def test_athlete_id_rejects_missing_or_non_positive_values(self) -> None:
        for value in (None, "not-a-number", 0, -1):
            with self.subTest(value=value), self.assertRaises(main.HTTPException) as error:
                main._athlete_id_from_body(value)
            self.assertEqual(error.exception.status_code, 422)

    async def test_general_chat_has_no_analytics_payload(self) -> None:
        message, analytics = await main._chat_payload(FakeRequest({"athlete_id": 42, "message": "Hello"}))

        self.assertEqual(message, "Hello")
        self.assertEqual(analytics, "")

    async def test_trend_chat_builds_analytics_payload(self) -> None:
        pool = object()
        main.app.state.db_pool = pool
        request = FakeRequest(
            {"athlete_id": "42", "message": "Show my sleep trend over the last 7 days", "timezone": "UTC"}
        )

        with patch.object(main, "TrendService", FakeTrendService):
            message, analytics = await main._chat_payload(request)

        self.assertEqual(message, "Show my sleep trend over the last 7 days")
        self.assertEqual(FakeTrendService.calls[0][0], pool)
        self.assertEqual(FakeTrendService.calls[0][1], 42)
        self.assertEqual(FakeTrendService.calls[0][2].metric, "sleep_score")
        self.assertEqual(analytics, '{"metric":"sleep_score","summary":{"trend":"increasing"}}')

    async def test_trend_chat_requires_configured_database(self) -> None:
        request = FakeRequest({"athlete_id": 42, "message": "Show my sleep trend over the last 7 days"})

        with self.assertRaises(main.HTTPException) as error:
            await main._chat_payload(request)

        self.assertEqual(error.exception.status_code, 503)
