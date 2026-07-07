"""
Exam Sprint Rule-Based Tools
=============================

Pure-logic tools for the Exam Sprint capability.
Zero LLM token consumption — all outputs are computed deterministically.

Tools:
    - TimePressureTool: Score time urgency (0.0–1.0) based on exam date.
    - WeakPointRankerTool: Rank knowledge points by mastery gap.
    - PlanBuilderTool: Build a sprint task list from weak points + time pressure.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

from deeptutor.core.tool_protocol import (
    BaseTool,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)


# ---------------------------------------------------------------------------
# 1. TimePressureTool
# ---------------------------------------------------------------------------


class TimePressureTool(BaseTool):
    """Compute a time-pressure score (0.0–1.0) from days remaining.

    Score interpretation:
        0.0  = exam is far away (>= 30 days)
        0.5  = ~14 days remaining
        1.0  = exam is tomorrow or overdue
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="time_pressure",
            description=(
                "Calculate time pressure for an exam based on today's date "
                "and the exam date. Returns a score from 0.0 (no pressure) "
                "to 1.0 (critical)."
            ),
            parameters=[
                ToolParameter(
                    name="exam_date",
                    type="string",
                    description="Exam date in ISO format (YYYY-MM-DD).",
                ),
                ToolParameter(
                    name="today",
                    type="string",
                    description="Today's date in ISO format (YYYY-MM-DD). Optional, defaults to server date.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        exam_date_str: str = kwargs["exam_date"]
        today_str: str | None = kwargs.get("today")

        exam_date = date.fromisoformat(exam_date_str)
        today = date.fromisoformat(today_str) if today_str else date.today()

        days_remaining = (exam_date - today).days

        # Score: exponential decay, 0.5 at ~14 days
        score = _time_pressure_score(days_remaining)

        result = {
            "exam_date": exam_date_str,
            "today": today.isoformat(),
            "days_remaining": days_remaining,
            "score": round(score, 3),
            "level": _pressure_level(score),
        }
        return ToolResult(content=str(result), metadata=result)


def _time_pressure_score(days_remaining: int) -> float:
    """Exponential decay: 0.5 at 14 days, approaches 1.0 as days -> 0."""
    if days_remaining <= 0:
        return 1.0
    # score = 1 - (days_remaining / 30) ^ 0.6, clamped [0, 1]
    raw = 1.0 - (days_remaining / 30.0) ** 0.6
    return max(0.0, min(1.0, raw))


def _pressure_level(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.5:
        return "high"
    if score >= 0.2:
        return "moderate"
    return "low"


# ---------------------------------------------------------------------------
# 2. WeakPointRankerTool
# ---------------------------------------------------------------------------


class WeakPointRankerTool(BaseTool):
    """Rank knowledge points by weakness (mastery gap from target)."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="weak_point_ranker",
            description=(
                "Rank knowledge points from weakest to strongest based on "
                "mastery scores. Returns sorted list with gap analysis."
            ),
            parameters=[
                ToolParameter(
                    name="mastery_data",
                    type="array",
                    description=(
                        'Array of objects with "name" (str), "score" (float 0-1), '
                        'and optional "surface" (str).'
                    ),
                ),
                ToolParameter(
                    name="target_score",
                    type="number",
                    description="Target mastery score (0.0–1.0). Default 0.7.",
                    required=False,
                    default=0.7,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        mastery_data: list[dict[str, Any]] = kwargs["mastery_data"]
        target: float = kwargs.get("target_score", 0.7)

        ranked = _rank_weak_points(mastery_data, target)

        result = {
            "target_score": target,
            "total_points": len(ranked),
            "below_target": sum(1 for r in ranked if r["gap"] > 0),
            "ranked": ranked,
        }
        return ToolResult(content=str(result), metadata=result)


def _rank_weak_points(
    mastery_data: list[dict[str, Any]],
    target: float,
) -> list[dict[str, Any]]:
    """Sort by gap descending (weakest first)."""
    ranked = []
    for entry in mastery_data:
        score = float(entry.get("score", 0))
        gap = max(0.0, target - score)
        rounded_gap = round(gap, 3)
        ranked.append(
            {
                "name": entry.get("name", "unknown"),
                "surface": entry.get("surface", "unknown"),
                "score": round(score, 3),
                "gap": rounded_gap,
                "priority": _priority_from_gap(rounded_gap),
            }
        )
    ranked.sort(key=lambda r: r["gap"], reverse=True)
    return ranked


def _priority_from_gap(gap: float) -> str:
    if gap >= 0.5:
        return "critical"
    if gap >= 0.3:
        return "high"
    if gap >= 0.1:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# 3. PlanBuilderTool
# ---------------------------------------------------------------------------


class PlanBuilderTool(BaseTool):
    """Build a sprint task list from weak points + time pressure."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="plan_builder",
            description=(
                "Generate a prioritized sprint task list from ranked weak "
                "points, time pressure, and available study hours."
            ),
            parameters=[
                ToolParameter(
                    name="ranked_weak_points",
                    type="array",
                    description="Output from weak_point_ranker tool (ranked list).",
                ),
                ToolParameter(
                    name="time_pressure",
                    type="number",
                    description="Time pressure score (0.0–1.0) from time_pressure tool.",
                ),
                ToolParameter(
                    name="days_remaining",
                    type="integer",
                    description="Days until exam.",
                ),
                ToolParameter(
                    name="daily_hours",
                    type="number",
                    description="Available study hours per day. Default 2.0.",
                    required=False,
                    default=2.0,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        ranked: list[dict[str, Any]] = kwargs["ranked_weak_points"]
        pressure: float = kwargs["time_pressure"]
        days: int = kwargs["days_remaining"]
        daily_hours: float = kwargs.get("daily_hours", 2.0)

        tasks = _build_tasks(ranked, pressure, days, daily_hours)

        result = {
            "total_tasks": len(tasks),
            "days_remaining": days,
            "daily_hours": daily_hours,
            "time_pressure": round(pressure, 3),
            "tasks": tasks,
        }
        return ToolResult(content=str(result), metadata=result)


def _build_tasks(
    ranked: list[dict[str, Any]],
    pressure: float,
    days: int,
    daily_hours: float,
) -> list[dict[str, Any]]:
    """Generate task list: critical topics first, spread across available days."""
    tasks = []
    total_hours = max(1, days * daily_hours)

    # Allocate time: critical = 40%, high = 30%, medium = 20%, low = 10%
    allocation = {"critical": 0.40, "high": 0.30, "medium": 0.20, "low": 0.10}

    for i, wp in enumerate(ranked):
        if wp["gap"] <= 0:
            continue  # skip topics already at target

        pct = allocation.get(wp["priority"], 0.10)
        # Scale up allocation under high pressure (focus on critical)
        if pressure >= 0.7 and wp["priority"] == "critical":
            pct = min(0.60, pct * 1.5)

        hours = max(0.5, round(total_hours * pct, 1))
        sessions = max(1, round(hours / max(0.5, daily_hours * 0.3)))

        tasks.append(
            {
                "id": i + 1,
                "topic": wp["name"],
                "surface": wp.get("surface", "unknown"),
                "priority": wp["priority"],
                "current_score": wp["score"],
                "gap": wp["gap"],
                "action": "learn" if wp["gap"] > 0.3 else "practice",
                "estimated_hours": hours,
                "sessions": sessions,
            }
        )

    # Sort by priority order
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tasks.sort(key=lambda t: priority_order.get(t["priority"], 9))

    return tasks
