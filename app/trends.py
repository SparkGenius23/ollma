from __future__ import annotations

import asyncio
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
    "hrv_score": {"label": "HRV", "table": "ts_model_output_recovery_score", "column": "hrv_score"},
    "rhr_score": {
        "label": "Resting heart rate",
        "table": "ts_model_output_recovery_score",
        "column": "rhr_score",
    },
    "sleep_score": {"label": "Sleep", "table": "ts_model_output_recovery_score", "column": "sleep_score"},
    "nutrition_ratio": {
        "label": "Nutrition",
        "table": "ts_model_output_recovery_score",
        "column": "nutrition_ratio",
    },
    "hydration_score": {
        "label": "Hydration",
        "table": "ts_model_output_recovery_score",
        "column": "hydration_score",
    },
    "ari_score": {"label": "ARI", "table": "ts_model_output_recovery_score", "column": "ari_score"},
    "spo2_score": {"label": "SpO2", "table": "ts_model_output_recovery_score", "column": "spo2_score"},
    "stress_score": {"label": "Stress", "table": "ts_model_output_recovery_score", "column": "stress_score"},
    "soreness_score": {
        "label": "Soreness",
        "table": "ts_model_output_recovery_score",
        "column": "soreness_score",
    },
    "fatigue_score": {
        "label": "Fatigue",
        "table": "ts_model_output_recovery_score",
        "column": "fatigue_score",
    },
}

# These recovery inputs provide the context needed to compare a score trend with
# the athlete's daily wellness signals.  Like METRICS, all identifiers here are
# fixed server-side rather than coming from the chat request.
COMPARISON_METRICS = {
    "hrv_score": "HRV",
    "rhr_score": "Resting heart rate",
    "sleep_score": "Sleep",
    "nutrition_ratio": "Nutrition",
    "hydration_score": "Hydration",
    "ari_score": "ARI",
    "spo2_score": "SpO2",
    "stress_score": "Stress",
    "soreness_score": "Soreness",
    "fatigue_score": "Fatigue",
}
RECOVERY_TABLE = "ts_model_output_recovery_score"


class TrendService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def build_payload(
        self, athlete_id: int, intent: ChatIntent, start_date: date, end_date: date
    ) -> dict[str, Any]:
        logger.info(
            "Trend request validation started",
            extra={
                "intent": intent.intent.value,
                "metric": intent.metric,
                "comparison_metric": intent.comparison_metric,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        if intent.intent == IntentType.METRIC_COMPARISON:
            return await self._metric_comparison(athlete_id, intent, start_date, end_date)
        payload, comparison_metrics = await asyncio.gather(
            self._single_metric(athlete_id, intent.metric, start_date, end_date),
            self._comparison_metrics(athlete_id, start_date, end_date),
        )
        payload["comparison_metrics"] = comparison_metrics
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

    async def _comparison_metrics(
        self, athlete_id: int, start_date: date, end_date: date
    ) -> dict[str, Any]:
        """Fetch daily recovery inputs once for score-trend comparison."""
        columns = ", ".join(COMPARISON_METRICS)
        query = f"""
            SELECT date, {columns}
            FROM (
                SELECT DISTINCT ON (date) date, {columns}
                FROM {RECOVERY_TABLE}
                WHERE user_id = $1
                  AND date BETWEEN $2 AND $3
                ORDER BY date, time DESC
            ) AS latest_daily_recovery_inputs
            ORDER BY date
        """
        rows = await self.pool.fetch(query, athlete_id, start_date, end_date)
        requested_days = (end_date - start_date).days + 1
        metrics: dict[str, Any] = {}
        for metric, label in COMPARISON_METRICS.items():
            values = [
                {"date": row["date"].isoformat(), "value": float(row[metric])}
                for row in rows
                if row[metric] is not None
            ]
            scores = [value["value"] for value in values]
            metrics[metric] = {
                "label": label,
                "daily_values": values,
                "summary": _comparison_summary(scores),
                "data_quality": {
                    "requested_days": requested_days,
                    "available_days": len(values),
                    "confidence": "high" if len(values) == requested_days else "limited",
                },
            }
        logger.info(
            "Trend comparison data completed",
            extra={
                "requested_days": requested_days,
                "available_days": len(rows),
                "metrics": list(COMPARISON_METRICS),
            },
        )
        return metrics

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
        summary = _summary(scores, metric)
        logger.info(
            "Trend data validation completed",
            extra={
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
        }

    async def _metric_comparison(
        self, athlete_id: int, intent: ChatIntent, start_date: date, end_date: date
    ) -> dict[str, Any]:
        left, right, comparison_metrics = await asyncio.gather(
            self._single_metric(athlete_id, intent.metric, start_date, end_date),
            self._single_metric(athlete_id, intent.comparison_metric, start_date, end_date),
            self._comparison_metrics(athlete_id, start_date, end_date),
        )
        return {
            "comparison_type": "metric_vs_metric",
            "period": left["period"],
            "metrics": [left, right],
            "comparison_metrics": comparison_metrics,
            "data_quality": {
                "left": left["data_quality"],
                "right": right["data_quality"],
            },
        }


def _difference(current: float | None, previous: float | None) -> float | None:
    return round(current - previous, 1) if current is not None and previous is not None else None


def _summary(scores: list[float], metric: str) -> dict[str, Any]:
    return {
        "average": round(mean(scores), 1) if scores else None,
        "minimum": min(scores) if scores else None,
        "maximum": max(scores) if scores else None,
        "start_value": scores[0] if scores else None,
        "end_value": scores[-1] if scores else None,
        "absolute_change": scores[-1] - scores[0] if len(scores) >= 2 else None,
        "trend": _trend(scores, metric),
    }


def _comparison_summary(scores: list[float]) -> dict[str, Any]:
    """Summarize a supporting input without implying a health direction."""
    summary = _summary(scores, "supporting_metric")
    summary["trend"] = _direction(scores)
    return summary


def _direction(scores: list[float]) -> str:
    if len(scores) < 2:
        return "insufficient_data"
    if scores[-1] == scores[0]:
        return "stable"
    return "increasing" if scores[-1] > scores[0] else "decreasing"


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
