from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    CURRENT = "current"
    TREND = "trend"
    PERIOD_COMPARISON = "period_comparison"
    METRIC_COMPARISON = "metric_comparison"
    GENERAL = "general"


METRICS = {
    "recovery": "recovery_score",
    "readiness": "readiness_score",
    "injury risk": "injury_risk_score",
    "injury-risk": "injury_risk_score",
    "risk": "injury_risk_score",
}


@dataclass(frozen=True)
class ChatIntent:
    intent: IntentType
    metric: str | None = None
    comparison_metric: str | None = None
    days: int | None = None
    compare_previous_period: bool = False


def parse_intent(message: str) -> ChatIntent:
    """Parse the supported score-history phrases without allowing arbitrary SQL."""
    normalized = " ".join(message.lower().split())
    matched_metrics = [
        (match.start(), column)
        for phrase, column in METRICS.items()
        if (match := re.search(rf"\b{re.escape(phrase)}\b", normalized))
    ]
    matched_metrics.sort()
    matched_columns = [column for _, column in matched_metrics]
    metric = matched_columns[0] if matched_columns else None
    unique_metrics = list(dict.fromkeys(matched_columns))
    days_match = re.search(r"\b(?:last|past|previous)\s+(\d{1,3})\s+days?\b", normalized)
    days = int(days_match.group(1)) if days_match else None
    if "week" in normalized and days is None:
        days = 7

    comparison_words = ("compare", "comparison", "versus", "vs", "against")
    trend_words = ("trend", "improve", "improved", "change", "history", "last", "past", "week")
    previous_words = ("previous period", "prior period", "last week", "compared to last", "since last week")

    if len(unique_metrics) >= 2:
        result = ChatIntent(IntentType.METRIC_COMPARISON, unique_metrics[0], unique_metrics[1], days or 7)
        logger.info(
            "Intent validation succeeded: metric comparison",
            extra={
                "intent": result.intent.value,
                "metric": result.metric,
                "comparison_metric": result.comparison_metric,
                "days": result.days,
            },
        )
        return result
    if metric and any(word in normalized for word in comparison_words):
        result = ChatIntent(
            IntentType.PERIOD_COMPARISON,
            metric,
            days=days or 7,
            compare_previous_period=any(word in normalized for word in previous_words),
        )
    elif metric and any(word in normalized for word in trend_words):
        result = ChatIntent(
            IntentType.TREND,
            metric,
            days=days or 7,
            compare_previous_period=any(word in normalized for word in previous_words),
        )
    elif metric:
        result = ChatIntent(IntentType.CURRENT, metric)
    else:
        result = ChatIntent(IntentType.GENERAL)

    logger.info(
        "Intent validation completed",
        extra={
            "intent": result.intent.value,
            "metric": result.metric,
            "comparison_metric": result.comparison_metric,
            "days": result.days,
            "compare_previous_period": result.compare_previous_period,
        },
    )
    return result


def date_range_for(intent: ChatIntent, athlete_today: date) -> tuple[date, date] | None:
    if intent.days is None:
        logger.debug(
            "Date-range validation skipped: intent has no period",
            extra={"intent": intent.intent.value},
        )
        return None
    start_date = athlete_today - timedelta(days=intent.days) + timedelta(days=1)
    logger.debug(
        "Date-range validation completed",
        extra={
            "intent": intent.intent.value,
            "days": intent.days,
            "start_date": start_date.isoformat(),
            "end_date": athlete_today.isoformat(),
        },
    )
    return start_date, athlete_today
