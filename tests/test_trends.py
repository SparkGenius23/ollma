import sys
import types
import unittest
from datetime import date

# Let these isolated unit tests run without a database-driver installation. The
# service only needs asyncpg for its type annotation; the pool is faked below.
try:
    import asyncpg  # noqa: F401
except ModuleNotFoundError:
    asyncpg = types.ModuleType("asyncpg")
    asyncpg.Pool = object
    sys.modules["asyncpg"] = asyncpg

from app.intent import ChatIntent, IntentType
from app.trends import TrendService


class FakePool:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def fetch(self, query: str, *_args: object) -> list[dict[str, object]]:
        self.queries.append(query)
        if "latest_daily_recovery_inputs" in query:
            return [
                {
                    "date": date(2026, 9, 1),
                    "hrv_score": 50,
                    "rhr_score": 55,
                    "sleep_score": 70,
                    "nutrition_ratio": 60,
                    "hydration_score": 80,
                    "ari_score": None,
                    "spo2_score": 98,
                    "stress_score": 40,
                    "soreness_score": 20,
                    "fatigue_score": 30,
                },
                {
                    "date": date(2026, 9, 2),
                    "hrv_score": 55,
                    "rhr_score": 54,
                    "sleep_score": 75,
                    "nutrition_ratio": 65,
                    "hydration_score": 82,
                    "ari_score": None,
                    "spo2_score": 98,
                    "stress_score": 35,
                    "soreness_score": 18,
                    "fatigue_score": 25,
                },
            ]
        return [
            {"date": date(2026, 9, 1), "value": 70},
            {"date": date(2026, 9, 2), "value": 75},
        ]


class TrendServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_trend_includes_aligned_wellness_comparison_metrics(self) -> None:
        pool = FakePool()
        payload = await TrendService(pool).build_payload(
            42,
            ChatIntent(IntentType.TREND, "recovery_score", days=2),
            date(2026, 9, 1),
            date(2026, 9, 2),
        )

        sleep = payload["comparison_metrics"]["sleep_score"]
        self.assertEqual(payload["summary"]["trend"], "improving")
        self.assertEqual(sleep["daily_values"], [{"date": "2026-09-01", "value": 70.0}, {"date": "2026-09-02", "value": 75.0}])
        self.assertEqual(sleep["summary"]["trend"], "increasing")
        self.assertEqual(payload["comparison_metrics"]["fatigue_score"]["summary"]["trend"], "decreasing")
        self.assertEqual(payload["comparison_metrics"]["ari_score"]["summary"]["trend"], "insufficient_data")
        self.assertEqual(len(pool.queries), 2)

    async def test_metric_comparison_includes_supporting_metrics_once(self) -> None:
        pool = FakePool()
        payload = await TrendService(pool).build_payload(
            42,
            ChatIntent(IntentType.METRIC_COMPARISON, "recovery_score", "sleep_score", days=2),
            date(2026, 9, 1),
            date(2026, 9, 2),
        )

        self.assertEqual(payload["comparison_type"], "metric_vs_metric")
        self.assertEqual([metric["metric"] for metric in payload["metrics"]], ["recovery_score", "sleep_score"])
        self.assertIn("nutrition_ratio", payload["comparison_metrics"])
        self.assertEqual(len(pool.queries), 3)
