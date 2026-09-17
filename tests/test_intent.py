from datetime import date
import unittest

from app.intent import IntentType, date_range_for, parse_intent


class ParseIntentTests(unittest.TestCase):
    def test_parses_wellness_trend(self) -> None:
        intent = parse_intent("Show my sleep trend over the last 14 days")

        self.assertEqual(intent.intent, IntentType.TREND)
        self.assertEqual(intent.metric, "sleep_score")
        self.assertEqual(intent.days, 14)

    def test_parses_wellness_metric_comparison(self) -> None:
        intent = parse_intent("Compare my recovery versus sleep over the last 7 days")

        self.assertEqual(intent.intent, IntentType.METRIC_COMPARISON)
        self.assertEqual(intent.metric, "recovery_score")
        self.assertEqual(intent.comparison_metric, "sleep_score")
        self.assertEqual(intent.days, 7)

    def test_date_range_is_inclusive(self) -> None:
        intent = parse_intent("Show my nutrition trend over the last 7 days")

        self.assertEqual(date_range_for(intent, date(2026, 9, 17)), (date(2026, 9, 11), date(2026, 9, 17)))
