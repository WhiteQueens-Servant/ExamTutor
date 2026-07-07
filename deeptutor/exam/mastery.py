"""
Exam Mastery Store
==================

Persistent mastery scores for the Exam Sprint dashboard.

Data is stored as a JSON file under the runtime data root, separate from
L2 memory (which holds unstructured markdown knowledge entries).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# File path: <data_root>/exam_sprint/mastery.json
_MASTERY_DIR = "exam_sprint"
_MASTERY_FILE = "mastery.json"


def _mastery_path() -> Path:
    """Resolve the mastery JSON file path."""
    from deeptutor.runtime.home import get_runtime_data_root

    return get_runtime_data_root() / _MASTERY_DIR / _MASTERY_FILE


def load_mastery() -> list[dict[str, Any]]:
    """Load mastery entries from disk.

    Returns a list of dicts, each with keys:
    - knowledge_point: str
    - score: float (0.0 - 1.0)
    - surface: str (notebook|quiz|chat|kb|book)
    """
    path = _mastery_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load mastery data: %s", exc)
        return []


def save_mastery(entries: list[dict[str, Any]]) -> None:
    """Persist mastery entries to disk."""
    path = _mastery_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)
    logger.info("Saved %d mastery entries", len(entries))


def update_mastery_score(
    knowledge_point: str,
    new_score: float,
    surface: str = "quiz",
) -> list[dict[str, Any]]:
    """Update (or create) a single mastery entry.

    Uses exponential moving average to blend new score with existing:
        updated = 0.7 * old + 0.3 * new

    Returns the full updated mastery list.
    """
    entries = load_mastery()
    score = max(0.0, min(1.0, new_score))  # clamp to [0, 1]

    for entry in entries:
        if entry.get("knowledge_point") == knowledge_point:
            old_score = entry.get("score", 0.0)
            # Exponential moving average
            blended = round(0.7 * old_score + 0.3 * score, 3)
            entry["score"] = blended
            entry["surface"] = surface
            logger.info(
                "Updated mastery: %s %.2f -> %.2f (blended with old %.2f)",
                knowledge_point, old_score, blended, score,
            )
            save_mastery(entries)
            return entries

    # New entry
    entries.append({
        "knowledge_point": knowledge_point,
        "score": score,
        "surface": surface,
    })
    logger.info("Created mastery: %s %.2f", knowledge_point, score)
    save_mastery(entries)
    return entries
