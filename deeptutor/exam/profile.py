"""
Exam Sprint Profile Store
=========================

Unified user profile + mastery scores for the Exam Sprint dashboard.

Replaces the legacy mastery.json with a single profile.json that serves
as both the system-facing AbilityProfile and the user-facing Mastery Report.

Storage: <data_root>/exam_sprint/profile.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROFILE_DIR = "exam_sprint"
_PROFILE_FILE = "profile.json"

DEFAULT_PROFILE: dict[str, Any] = {
    "exam_name": "",
    "created_at": "",
    "last_updated": "",
    "knowledge_points": [],
    "diagnosis": None,
}


def _profile_path() -> Path:
    """Resolve the profile JSON file path."""
    from deeptutor.runtime.home import get_runtime_data_root

    return get_runtime_data_root() / _PROFILE_DIR / _PROFILE_FILE


def _now_iso() -> str:
    """Return current time as ISO datetime string."""
    return datetime.now(timezone.utc).isoformat()


def load_profile() -> dict[str, Any]:
    """Load the full profile from disk.

    Returns a dict with keys: exam_name, created_at, last_updated,
    knowledge_points, diagnosis. Returns DEFAULT_PROFILE if no file exists.
    """
    path = _profile_path()
    if not path.exists():
        return {**DEFAULT_PROFILE}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {**DEFAULT_PROFILE, **data}
        return {**DEFAULT_PROFILE}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load profile: %s", exc)
        return {**DEFAULT_PROFILE}


def save_profile(profile: dict[str, Any]) -> None:
    """Persist the full profile to disk."""
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    profile["last_updated"] = _now_iso()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)
    logger.info("Saved profile: %d knowledge_points", len(profile.get("knowledge_points", [])))


# ---------------------------------------------------------------------------
# Mastery-compatible API (drop-in replacement for mastery.py)
# ---------------------------------------------------------------------------


def load_mastery() -> list[dict[str, Any]]:
    """Load mastery entries in the legacy format expected by ExamMasteryTable.

    Returns a list of dicts, each with keys:
    - knowledge_point: str
    - score: float (0.0 - 1.0)
    - surface: str (notebook|quiz|chat|kb|book)

    This is a compatibility shim — reads from profile.json's knowledge_points.
    """
    profile = load_profile()
    entries = []
    for kp in profile.get("knowledge_points", []):
        entries.append({
            "knowledge_point": kp.get("name", ""),
            "score": kp.get("score", 0.0),
            "surface": kp.get("last_surface", "quiz"),
        })
    return entries


def update_mastery_score(
    knowledge_point: str,
    new_score: float,
    surface: str = "quiz",
) -> list[dict[str, Any]]:
    """Update (or create) a single knowledge point's mastery score.

    Uses exponential moving average for existing entries:
        updated = 0.7 * old + 0.3 * new

    For new entries (first time), writes the raw score directly.

    Returns the legacy-format mastery list (for API compatibility).
    """
    profile = load_profile()
    kps = profile.get("knowledge_points", [])
    score = max(0.0, min(1.0, new_score))  # clamp to [0, 1]

    for kp in kps:
        if kp.get("name") == knowledge_point:
            old_score = kp.get("score", 0.0)
            # EMA blend for existing entries
            blended = round(0.7 * old_score + 0.3 * score, 3)
            kp["score"] = blended
            kp["last_surface"] = surface
            kp["last_practiced"] = _now_iso()
            kp["practice_count"] = kp.get("practice_count", 0) + 1
            logger.info(
                "Updated mastery: %s %.2f -> %.2f (blended with old %.2f)",
                knowledge_point, old_score, blended, score,
            )
            save_profile(profile)
            return load_mastery()

    # New entry — direct write, no EMA
    kps.append({
        "name": knowledge_point,
        "chapter": "",
        "score": score,
        "total_questions": 0,
        "correct": 0,
        "error_types": [],
        "last_practiced": _now_iso(),
        "practice_count": 1,
        "last_surface": surface,
    })
    profile["knowledge_points"] = kps
    logger.info("Created mastery: %s %.2f", knowledge_point, score)
    save_profile(profile)
    return load_mastery()


# ---------------------------------------------------------------------------
# Profile-specific operations
# ---------------------------------------------------------------------------


def init_from_diagnosis(
    exam_name: str,
    diagnosis_result: dict[str, Any],
) -> dict[str, Any]:
    """Initialize profile from a completed diagnosis.

    Args:
        exam_name: The exam name (e.g. "计算机网络 期末考试")
        diagnosis_result: Dict with keys:
            - questions: list of {question_id, question, correct_answer, user_answer, is_correct, error_type, knowledge_point}
            - overall_score: float
            - weak_points: list[str]
            - strong_points: list[str]

    Returns the full updated profile.
    """
    profile = load_profile()
    profile["exam_name"] = exam_name
    if not profile.get("created_at"):
        profile["created_at"] = _now_iso()

    # Aggregate knowledge points from diagnosis questions
    kp_stats: dict[str, dict[str, Any]] = {}
    for q in diagnosis_result.get("questions", []):
        kp_name = q.get("knowledge_point", "unknown")
        if kp_name not in kp_stats:
            kp_stats[kp_name] = {
                "name": kp_name,
                "chapter": "",
                "score": 0.0,
                "total_questions": 0,
                "correct": 0,
                "error_types": [],
                "last_practiced": _now_iso(),
                "practice_count": 0,
                "last_surface": "diagnosis",
            }
        stats = kp_stats[kp_name]
        stats["total_questions"] += 1
        if q.get("is_correct"):
            stats["correct"] += 1
        else:
            err = q.get("error_type", "")
            if err and err not in stats["error_types"]:
                stats["error_types"].append(err)

    # Calculate scores
    for kp_name, stats in kp_stats.items():
        if stats["total_questions"] > 0:
            stats["score"] = round(stats["correct"] / stats["total_questions"], 3)

    profile["knowledge_points"] = list(kp_stats.values())

    # Store diagnosis report
    profile["diagnosis"] = {
        "completed_at": _now_iso(),
        "total_questions": diagnosis_result.get("total_questions", 0),
        "correct": sum(1 for q in diagnosis_result.get("questions", []) if q.get("is_correct")),
        "overall_score": diagnosis_result.get("overall_score", 0.0),
        "questions": diagnosis_result.get("questions", []),
        "weak_points": diagnosis_result.get("weak_points", []),
        "strong_points": diagnosis_result.get("strong_points", []),
    }

    save_profile(profile)
    logger.info(
        "Initialized profile from diagnosis: %d knowledge points, overall=%.2f",
        len(profile["knowledge_points"]),
        profile["diagnosis"]["overall_score"],
    )
    return profile


def reset_profile() -> None:
    """Clear the profile file (used during full state reset)."""
    path = _profile_path()
    if path.exists():
        path.unlink()
        logger.info("Deleted profile: %s", path)
