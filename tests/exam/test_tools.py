"""
Tests for Exam Sprint rule-based tools.

Pure logic — no LLM, no backend server required.
Run with: pytest tests/exam/test_tools.py -v
"""

import pytest

from deeptutor.exam.tools import (
    PlanBuilderTool,
    TimePressureTool,
    WeakPointRankerTool,
    _priority_from_gap,
    _time_pressure_score,
)


# ── TimePressureTool ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_time_pressure_far_away():
    """30 days out should be low pressure (< 0.2)."""
    tool = TimePressureTool()
    result = await tool.execute(exam_date="2026-08-06", today="2026-07-07")
    meta = result.metadata
    assert meta["days_remaining"] == 30
    assert meta["score"] < 0.2
    assert meta["level"] == "low"


@pytest.mark.asyncio
async def test_time_pressure_tomorrow():
    """1 day out should be critical (> 0.8)."""
    tool = TimePressureTool()
    result = await tool.execute(exam_date="2026-07-08", today="2026-07-07")
    meta = result.metadata
    assert meta["days_remaining"] == 1
    assert meta["score"] > 0.8
    assert meta["level"] == "critical"


@pytest.mark.asyncio
async def test_time_pressure_overdue():
    """Past exam date should return 1.0."""
    tool = TimePressureTool()
    result = await tool.execute(exam_date="2026-07-01", today="2026-07-07")
    meta = result.metadata
    assert meta["days_remaining"] == -6
    assert meta["score"] == 1.0
    assert meta["level"] == "critical"


@pytest.mark.asyncio
async def test_time_pressure_two_weeks():
    """14 days should be around 0.5 (moderate/high boundary)."""
    tool = TimePressureTool()
    result = await tool.execute(exam_date="2026-07-21", today="2026-07-07")
    meta = result.metadata
    assert meta["days_remaining"] == 14
    assert 0.3 < meta["score"] < 0.7


def test_time_pressure_score_unit():
    """Direct unit test for the score function."""
    assert _time_pressure_score(0) == 1.0
    assert _time_pressure_score(-5) == 1.0
    assert _time_pressure_score(30) < 0.2
    assert _time_pressure_score(60) < 0.05


# ── WeakPointRankerTool ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weak_point_ranker_basic():
    """Weakest topics should come first."""
    tool = WeakPointRankerTool()
    mastery = [
        {"name": "TCP/IP", "score": 0.9},
        {"name": "DNS", "score": 0.3},
        {"name": "HTTP", "score": 0.6},
    ]
    result = await tool.execute(mastery_data=mastery)
    meta = result.metadata

    assert meta["total_points"] == 3
    assert meta["below_target"] == 2  # DNS (0.3) and HTTP (0.6) below 0.7

    ranked = meta["ranked"]
    assert ranked[0]["name"] == "DNS"
    assert ranked[1]["name"] == "HTTP"
    assert ranked[2]["name"] == "TCP/IP"


@pytest.mark.asyncio
async def test_weak_point_ranker_custom_target():
    """Custom target score should change gap calculation."""
    tool = WeakPointRankerTool()
    mastery = [{"name": "Topic A", "score": 0.8}]
    result = await tool.execute(mastery_data=mastery, target_score=0.9)
    meta = result.metadata

    assert meta["ranked"][0]["gap"] == 0.1
    assert meta["ranked"][0]["priority"] == "medium"


@pytest.mark.asyncio
async def test_weak_point_ranker_all_at_target():
    """No gap when all topics meet target."""
    tool = WeakPointRankerTool()
    mastery = [
        {"name": "A", "score": 0.9},
        {"name": "B", "score": 0.8},
    ]
    result = await tool.execute(mastery_data=mastery, target_score=0.7)
    meta = result.metadata
    assert meta["below_target"] == 0
    assert all(r["gap"] == 0 for r in meta["ranked"])


def test_priority_from_gap_unit():
    """Direct unit test for priority mapping."""
    assert _priority_from_gap(0.6) == "critical"
    assert _priority_from_gap(0.4) == "high"
    assert _priority_from_gap(0.15) == "medium"
    assert _priority_from_gap(0.05) == "low"
    assert _priority_from_gap(0.0) == "low"


# ── PlanBuilderTool ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_plan_builder_basic():
    """Should generate tasks sorted by priority, critical first."""
    tool = PlanBuilderTool()
    ranked = [
        {"name": "DNS", "score": 0.2, "gap": 0.5, "priority": "critical"},
        {"name": "HTTP", "score": 0.5, "gap": 0.2, "priority": "medium"},
        {"name": "TCP", "score": 0.9, "gap": 0.0, "priority": "low"},
    ]
    result = await tool.execute(
        ranked_weak_points=ranked,
        time_pressure=0.7,
        days_remaining=7,
        daily_hours=2.0,
    )
    meta = result.metadata

    assert meta["total_tasks"] == 2  # TCP has gap=0, skipped
    tasks = meta["tasks"]
    assert tasks[0]["topic"] == "DNS"
    assert tasks[0]["action"] == "learn"  # gap > 0.3
    assert tasks[1]["topic"] == "HTTP"
    assert tasks[1]["action"] == "practice"  # gap <= 0.3


@pytest.mark.asyncio
async def test_plan_builder_high_pressure_boosts_critical():
    """Under high pressure, critical topics get proportionally more time."""
    tool = PlanBuilderTool()
    ranked = [
        {"name": "A", "score": 0.1, "gap": 0.6, "priority": "critical"},
        {"name": "B", "score": 0.4, "gap": 0.3, "priority": "high"},
    ]

    # Same timeframe (14 days), different pressure levels
    result_normal = await tool.execute(
        ranked_weak_points=ranked, time_pressure=0.3, days_remaining=14, daily_hours=2.0
    )
    result_pressure = await tool.execute(
        ranked_weak_points=ranked, time_pressure=0.8, days_remaining=14, daily_hours=2.0
    )

    hours_normal = result_normal.metadata["tasks"][0]["estimated_hours"]
    hours_pressure = result_pressure.metadata["tasks"][0]["estimated_hours"]

    # High pressure should allocate MORE time to critical topic
    assert hours_pressure > hours_normal


@pytest.mark.asyncio
async def test_plan_builder_empty_ranked():
    """Empty ranked list should produce zero tasks."""
    tool = PlanBuilderTool()
    result = await tool.execute(
        ranked_weak_points=[], time_pressure=0.5, days_remaining=10, daily_hours=2.0
    )
    assert result.metadata["total_tasks"] == 0
    assert result.metadata["tasks"] == []
