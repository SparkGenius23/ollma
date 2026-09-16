from __future__ import annotations

import logging
from datetime import date, timedelta
from statistics import mean
from typing import Any
import asyncpg

from app.intent import ChatIntent, IntentType


logger = logging.getLogger(__name__)


METRICS = {
    "recovery_score": {
        "label": "Recovery",
        "table": "ts_model_output_recovery_score",
        "column": "recovery_score",
    },
    "readiness_score": {
        "label": "Readiness",
        "table": "ts_model_output_readiness_index",
        "column": "readiness_score",
    },
    "injury_risk_score": {
        "label": "Injury risk",
        "table": "ts_model_output_risk_score",
        "column": "injury_risk_prob",
    },
}


class TrendService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def build_payload(
        self, athlete_id: int, intent: ChatIntent, start_date: date, end_date: date
    ) -> dict[str, Any]:
        logger.info(
            "Trend request validation started",
            extra={
                "athlete_id": athlete_id,
                "intent": intent.intent.value,
                "metric": intent.metric,
                "comparison_metric": intent.comparison_metric,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        if intent.intent == IntentType.METRIC_COMPARISON:
            return await self._metric_comparison(athlete_id, intent, start_date, end_date)
        payload = await self._single_metric(athlete_id, intent.metric, start_date, end_date)
        if intent.compare_previous_period:
            days = (end_date - start_date).days + 1
            previous = await self._single_metric(
                athlete_id, intent.metric, start_date - timedelta(days=days), start_date - timedelta(days=1)
            )
            payload["comparison"] = {
                "previous_period_average": previous["summary"]["average"],
                "average_change": _difference(payload["summary"]["average"], previous["summary"]["average"]),
            }
        return payload

    async def _single_metric(
        self, athlete_id: int, metric: str | None, start_date: date, end_date: date
    ) -> dict[str, Any]:
        if metric not in METRICS:
            logger.warning("Trend metric validation failed", extra={"metric": metric})
            raise ValueError("Unsupported score metric")
        source = METRICS[metric]
        # Source identifiers are selected from METRICS, never supplied as free-form SQL.
        query = f"""
            SELECT date, value
            FROM (
                SELECT DISTINCT ON (date) date, {source['column']} AS value
                FROM {source['table']}
                WHERE user_id = $1
                  AND date BETWEEN $2 AND $3
                  AND {source['column']} IS NOT NULL
                ORDER BY date, time DESC
            ) AS latest_daily_score
            ORDER BY date
        """
        rows = await self.pool.fetch(query, athlete_id, start_date, end_date)
        values = [{"date": row["date"].isoformat(), "value": float(row["value"])} for row in rows]
        scores = [value["value"] for value in values]
        requested_days = (end_date - start_date).days + 1
        summary = {
            "average": round(mean(scores), 1) if scores else None,
            "minimum": min(scores) if scores else None,
            "maximum": max(scores) if scores else None,
            "start_value": scores[0] if scores else None,
            "end_value": scores[-1] if scores else None,
            "absolute_change": scores[-1] - scores[0] if len(scores) >= 2 else None,
            "trend": _trend(scores, metric),
        }
        logger.info(
            "Trend data validation completed",
            extra={
                "athlete_id": athlete_id,
                "metric": metric,
                "requested_days": requested_days,
                "available_days": len(values),
                "confidence": "high" if len(values) == requested_days else "limited",
            },
        )
        return {
            "metric": metric,
            "label": source["label"],
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "daily_values": values,
            "summary": summary,
            "data_quality": {
                "requested_days": requested_days,
                "available_days": len(values),
                "confidence": "high" if len(values) == requested_days else "limited",
            },
            "source_table": source["table"],
        }

    async def _metric_comparison(
        self, athlete_id: int, intent: ChatIntent, start_date: date, end_date: date
    ) -> dict[str, Any]:
        left = await self._single_metric(athlete_id, intent.metric, start_date, end_date)
        right = await self._single_metric(athlete_id, intent.comparison_metric, start_date, end_date)
        return {
            "comparison_type": "metric_vs_metric",
            "period": left["period"],
            "metrics": [left, right],
            "data_quality": {
                "left": left["data_quality"],
                "right": right["data_quality"],
            },
        }


def _difference(current: float | None, previous: float | None) -> float | None:
    return round(current - previous, 1) if current is not None and previous is not None else None


def _trend(scores: list[float], metric: str) -> str:
    if len(scores) < 2:
        return "insufficient_data"
    delta = scores[-1] - scores[0]
    threshold = 0.03 if metric == "injury_risk_score" and max(abs(score) for score in scores) <= 1 else 3
    if abs(delta) < threshold:
        return "stable"
    if metric == "injury_risk_score":
        return "improving" if delta < 0 else "worsening"
    return "improving" if delta > 0 else "declining"
