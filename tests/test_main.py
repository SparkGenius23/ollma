import types
import unittest
from unittest.mock import AsyncMock, patch

from tests._compat import ensure_asyncpg, ensure_dotenv, ensure_fastapi, ensure_jwt, ensure_ollama


def _install_runtime_stubs() -> None:
    """Run request-routing unit tests without installing optional runtime packages."""

    ensure_asyncpg()
    ensure_dotenv()
    ensure_ollama()
    ensure_jwt()
    ensure_fastapi()


_install_runtime_stubs()

import main


class FakeTrendService:
    calls: list[tuple[object, int, object, object, object]] = []

    def __init__(self, pool: object) -> None:
        self.pool = pool

    async def build_payload(self, athlete_id: int, intent: object, start_date: object, end_date: object) -> dict[str, object]:
        self.calls.append((self.pool, athlete_id, intent, start_date, end_date))
        return {"metric": "sleep_score", "summary": {"trend": "increasing"}}


def _payload(
    message: str,
    athlete_id: int | None = None,
    timezone: object = "UTC",
) -> types.SimpleNamespace:
    return types.SimpleNamespace(athlete_id=athlete_id, text=message, timezone=timezone)


def _request(body: dict[str, object]) -> types.SimpleNamespace:
    async def json() -> dict[str, object]:
        return body

    return types.SimpleNamespace(json=json)


class MainRequestTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeTrendService.calls.clear()
        main.app.state.db_pool = None

    async def test_general_chat_does_not_require_athlete_id(self) -> None:
        message, analytics = await main._chat_payload(_request({"message": "Warm up badminton ideas"}))

        self.assertEqual(message, "Warm up badminton ideas")
        self.assertEqual(analytics, "")

    async def test_history_language_without_an_athlete_id_bypasses_database(self) -> None:
        message, analytics = await main._chat_payload(_request({"message": "Show my sleep trend over the last 7 days"}))

        self.assertEqual(message, "Show my sleep trend over the last 7 days")
        self.assertEqual(analytics, "")

    async def test_startup_keeps_gateway_available_when_database_is_down(self) -> None:
        with patch.object(main, "DATABASE_URL", "postgresql://unavailable"), patch.object(
            main.asyncpg,
            "create_pool",
            new=AsyncMock(side_effect=OSError("connection refused")),
            create=True,
        ):
            await main.startup()

        self.assertIsNone(main.app.state.db_pool)

    async def test_database_health_retries_an_unavailable_pool(self) -> None:
        class FakePool:
            async def fetchval(self, *_args: object, **_kwargs: object) -> object:
                return 1

        async def restore_pool() -> bool:
            main.app.state.db_pool = FakePool()
            return True

        main.app.state.db_pool = None
        with patch.object(main, "initialize_database_pool", new=AsyncMock(side_effect=restore_pool)) as retry:
            self.assertEqual(await main.database_health(), {"status": "ok", "database": "connected"})

        retry.assert_awaited_once()

    async def test_trend_chat_uses_authenticated_identity(self) -> None:
        pool = object()
        main.app.state.db_pool = pool
        payload = _request(
            {"athlete_id": 42, "message": "Show my sleep trend over the last 7 days", "timezone": "UTC"}
        )

        with patch.object(main, "TrendService", FakeTrendService):
            message, analytics = await main._chat_payload(payload)

        self.assertEqual(message, "Show my sleep trend over the last 7 days")
        self.assertEqual(FakeTrendService.calls[0][0], pool)
        self.assertEqual(FakeTrendService.calls[0][1], 42)
        self.assertEqual(FakeTrendService.calls[0][2].metric, "sleep_score")
        self.assertEqual(analytics, '{"metric":"sleep_score","summary":{"trend":"increasing"}}')

    async def test_trend_chat_requires_configured_database(self) -> None:
        with self.assertRaises(main.HTTPException) as error:
            await main._chat_payload(_request({"athlete_id": 42, "message": "Show my sleep trend over the last 7 days"}))

        self.assertEqual(error.exception.status_code, 503)

    async def test_intelligence_stream_rejects_unknown_engine_and_chat_alias(self) -> None:
        payload = _request({"content": "Evaluate recovery"})
        with patch.object(main, "stream_content", new=lambda *args, **kwargs: iter(())):
            with self.assertRaises(main.HTTPException) as error:
                await main.get_intelligence_stream(payload, "unknown", object())
            self.assertEqual(error.exception.status_code, 404)

            with self.assertRaises(main.HTTPException) as error:
                await main.get_intelligence_stream(payload, "chat", object())
            self.assertEqual(error.exception.status_code, 404)

    async def test_health_endpoints_do_not_leak_sensitive_state(self) -> None:
        class FakePool:
            async def fetchval(self, *_args: object, **_kwargs: object) -> object:
                return 1

        main.app.state.db_pool = FakePool()
        ready = await main.database_health()
        self.assertEqual(ready, {"status": "ok", "database": "connected"})
