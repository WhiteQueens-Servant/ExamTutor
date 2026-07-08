"""Practice history persistence — stores wrong questions for review."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "exam_sprint"


def _get_history_path(data_root: str | None = None) -> Path:
    root = Path(data_root) if data_root else _DEFAULT_DATA_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root / "practice_history.json"


def _load_history(data_root: str | None = None) -> list[dict[str, Any]]:
    path = _get_history_path(data_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_history(items: list[dict[str, Any]], data_root: str | None = None) -> None:
    path = _get_history_path(data_root)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def save_wrong_question(
    question: dict[str, Any],
    source: str = "practice",
    data_root: str | None = None,
) -> dict[str, Any]:
    """Save a wrong question to practice history.
    
    Args:
        question: Answer record with question_id, question, correct_answer, user_answer, etc.
        source: Source of the question (diagnosis, practice)
        data_root: Override data directory
    
    Returns:
        Saved record with id and timestamp
    """
    items = _load_history(data_root)
    
    record = {
        "id": str(uuid.uuid4())[:8],
        "question_id": question.get("question_id", ""),
        "question": question.get("question", ""),
        "question_type": question.get("question_type", "short_answer"),
        "options": question.get("options"),
        "correct_answer": question.get("correct_answer", ""),
        "user_answer": question.get("user_answer", ""),
        "error_type": question.get("error_type", ""),
        "knowledge_point": question.get("knowledge_point", "unknown"),
        "explanation": question.get("explanation", ""),
        "source": source,
        "saved_at": datetime.now().isoformat(),
    }
    
    items.insert(0, record)  # newest first
    _save_history(items, data_root)
    return record


def list_practice_history(
    knowledge_point: str | None = None,
    data_root: str | None = None,
) -> list[dict[str, Any]]:
    """List practice history, optionally filtered by knowledge point."""
    items = _load_history(data_root)
    if knowledge_point:
        items = [i for i in items if i.get("knowledge_point") == knowledge_point]
    return items


def get_practice_history(
    record_id: str,
    data_root: str | None = None,
) -> dict[str, Any] | None:
    """Get a specific practice history record by ID."""
    items = _load_history(data_root)
    for item in items:
        if item.get("id") == record_id:
            return item
    return None


def delete_practice_history(
    record_id: str,
    data_root: str | None = None,
) -> bool:
    """Delete a specific practice history record by ID."""
    items = _load_history(data_root)
    original_len = len(items)
    items = [i for i in items if i.get("id") != record_id]
    if len(items) < original_len:
        _save_history(items, data_root)
        return True
    return False


def clear_practice_history(data_root: str | None = None) -> int:
    """Clear all practice history. Returns number of items cleared."""
    items = _load_history(data_root)
    count = len(items)
    _save_history([], data_root)
    return count
