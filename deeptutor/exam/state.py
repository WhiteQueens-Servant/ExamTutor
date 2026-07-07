"""
Exam Sprint State Store
=======================

Persistent exam state for the Exam Sprint dashboard.

Stores exam metadata (name, date, phase, etc.) as a JSON file.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# File path: <data_root>/exam_sprint/state.json
_STATE_DIR = "exam_sprint"
_STATE_FILE = "state.json"

DEFAULT_STATE: dict[str, Any] = {
    "exam_name": "",
    "exam_date": "",  # ISO date YYYY-MM-DD
    "phase": "phase_planning",  # phase_planning | sprint_week | score_protection
    "streak": 0,
    "last_active": "",  # ISO datetime
    "daily_budget_minutes": 120,
    "total_tasks_today": 0,
    "completed_tasks_today": 0,
    "onboarding_completed": False,
    "diagnosis_completed": False,
    "kb_name": "",
}


def _state_path() -> Path:
    """Resolve the state JSON file path."""
    from deeptutor.runtime.home import get_runtime_data_root

    return get_runtime_data_root() / _STATE_DIR / _STATE_FILE


def load_state() -> dict[str, Any]:
    """Load exam state from disk.

    Returns a dict with keys: exam_name, exam_date, phase, streak, etc.
    Returns DEFAULT_STATE if no file exists.
    """
    path = _state_path()
    if not path.exists():
        return {**DEFAULT_STATE}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            # Merge with defaults to handle missing keys
            return {**DEFAULT_STATE, **data}
        return {**DEFAULT_STATE}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load exam state: %s", exc)
        return {**DEFAULT_STATE}


def save_state(state: dict[str, Any]) -> None:
    """Persist exam state to disk."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)
    logger.info("Saved exam state: exam_name=%s", state.get("exam_name", ""))


def is_cold_start() -> bool:
    """Check if this is a cold start (no exam state configured)."""
    state = load_state()
    return not state.get("exam_name") or not state.get("exam_date")


def update_state(**kwargs: Any) -> dict[str, Any]:
    """Update specific fields in the exam state.

    Returns the full updated state.
    """
    state = load_state()
    state.update(kwargs)
    save_state(state)
    return state


def reset_state() -> None:
    """Reset all exam state to defaults and delete profile/history files.

    This is a destructive operation — clears state.json, profile.json,
    learn_history/, and practice_history.json.
    """
    from deeptutor.exam.profile import reset_profile

    # Reset state.json to defaults
    save_state({**DEFAULT_STATE})

    # Delete profile.json
    reset_profile()

    # Delete learn_history directory
    from deeptutor.runtime.home import get_runtime_data_root

    base = get_runtime_data_root() / _STATE_DIR
    learn_dir = base / "learn_history"
    if learn_dir.exists():
        import shutil
        shutil.rmtree(learn_dir)
        logger.info("Deleted learn_history: %s", learn_dir)

    # Delete practice_history.json
    practice_file = base / "practice_history.json"
    if practice_file.exists():
        practice_file.unlink()
        logger.info("Deleted practice_history: %s", practice_file)

    logger.info("Full state reset completed")
