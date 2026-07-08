"""
Exam Sprint Tasks Store
======================

Persistent task list for the Exam Sprint dashboard.

Stores daily tasks generated from weak points + time pressure.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# File path: <data_root>/exam_sprint/tasks.json
_TASKS_DIR = "exam_sprint"
_TASKS_FILE = "tasks.json"


def _tasks_path() -> Path:
    """Resolve the tasks JSON file path."""
    from deeptutor.runtime.home import get_runtime_data_root

    return get_runtime_data_root() / _TASKS_DIR / _TASKS_FILE


def load_tasks() -> dict[str, Any]:
    """Load tasks from disk.

    Returns a dict with keys: tasks, generated_at, date.
    Returns empty structure if no file exists.
    """
    path = _tasks_path()
    if not path.exists():
        return {"tasks": [], "generated_at": "", "date": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:
        logger.exception("Failed to load tasks")
        return {"tasks": [], "generated_at": "", "date": ""}


def save_tasks(data: dict[str, Any]) -> None:
    """Save tasks to disk."""
    path = _tasks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved %d tasks", len(data.get("tasks", [])))


def generate_tasks_from_diagnosis(
    knowledge_points: list[dict[str, Any]],
    days_remaining: int,
    daily_hours: float = 2.0,
) -> dict[str, Any]:
    """Generate initial task list from diagnosis knowledge points.

    Uses weak point ranking and time pressure to create prioritized tasks.
    """
    # Calculate time pressure (0.0 - 1.0)
    # More days remaining = less pressure
    pressure = max(0.0, min(1.0, 1.0 - (days_remaining / 30)))

    # Rank knowledge points by score (ascending = weakest first)
    ranked = []
    for kp in knowledge_points:
        score = kp.get("score", 0.0)
        # Gap = how far from mastery (1.0)
        gap = max(0.0, 1.0 - score)
        if gap <= 0:
            continue  # skip mastered topics

        # Priority based on gap and time pressure
        if gap > 0.4 or (gap > 0.2 and pressure > 0.7):
            priority = "critical"
        elif gap > 0.3 or (gap > 0.15 and pressure > 0.5):
            priority = "high"
        elif gap > 0.2:
            priority = "medium"
        else:
            priority = "low"

        ranked.append({
            "name": kp.get("name", "unknown"),
            "score": score,
            "gap": round(gap, 3),
            "priority": priority,
            "surface": kp.get("last_surface", "quiz"),
        })

    # Sort by gap descending (weakest first)
    ranked.sort(key=lambda x: -x["gap"])

    # Build tasks
    tasks = []
    total_hours = max(1, days_remaining * daily_hours)
    allocation = {"critical": 0.40, "high": 0.30, "medium": 0.20, "low": 0.10}

    for i, wp in enumerate(ranked):
        pct = allocation.get(wp["priority"], 0.10)
        # Scale up allocation under high pressure
        if pressure >= 0.7 and wp["priority"] == "critical":
            pct = min(0.60, pct * 1.5)

        hours = max(0.5, round(total_hours * pct, 1))
        sessions = max(1, round(hours / max(0.5, daily_hours * 0.3)))

        tasks.append({
            "id": str(uuid.uuid4())[:8],
            "knowledge_point": wp["name"],
            "action": "learn" if wp["gap"] > 0.3 else "practice",
            "priority": wp["priority"],
            "estimated_minutes": round(hours * 60),
            "current_score": wp["score"],
            "gap": wp["gap"],
            "completed": False,
            "completed_at": None,
        })

    # Sort by priority order
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tasks.sort(key=lambda t: priority_order.get(t["priority"], 9))

    now = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "tasks": tasks,
        "generated_at": now,
        "date": today,
        "total_tasks": len(tasks),
        "completed_tasks": 0,
    }


def complete_task(task_id: str) -> dict[str, Any] | None:
    """Mark a task as completed.

    Returns the updated task list, or None if task not found.
    """
    data = load_tasks()
    tasks = data.get("tasks", [])

    for task in tasks:
        if task.get("id") == task_id:
            task["completed"] = True
            task["completed_at"] = datetime.now(timezone.utc).isoformat()
            break
    else:
        return None

    # Update completed count
    completed_count = sum(1 for t in tasks if t.get("completed"))
    data["completed_tasks"] = completed_count

    save_tasks(data)
    return data


def reset_tasks() -> None:
    """Clear all tasks."""
    save_tasks({"tasks": [], "generated_at": "", "date": ""})
