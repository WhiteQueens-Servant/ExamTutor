"""Learn history management for Exam Sprint.

Stores generated learning materials as Markdown files in:
    <data_root>/exam_sprint/learn_history/

File naming: YYYY-MM-DD_HH-MM_<sanitized_knowledge_point>.md
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default data root (overridable via env or config)
_DEFAULT_DATA_ROOT = os.path.join(os.getcwd(), "data")
_LEARN_HISTORY_DIR = "exam_sprint/learn_history"


def _get_history_dir(data_root: str | None = None) -> Path:
    """Get the learn history directory path."""
    root = data_root or _DEFAULT_DATA_ROOT
    history_dir = Path(root) / _LEARN_HISTORY_DIR
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir


def _sanitize_filename(name: str, max_len: int = 50) -> str:
    """Sanitize a string for use as a filename."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove extra spaces and underscores
    sanitized = re.sub(r'[_\s]+', '_', sanitized)
    # Truncate if too long
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len]
    return sanitized.strip('_')


def save_learn_content(
    knowledge_point: str,
    content: str,
    source: str = "llm",
    mastery_score: float = 0.5,
    data_root: str | None = None,
) -> dict[str, Any]:
    """Save learning content to a Markdown file.

    Args:
        knowledge_point: The knowledge point name.
        content: The Markdown content to save.
        source: The source of the content (llm, rag).
        mastery_score: The mastery score at time of generation.
        data_root: Optional data root directory.

    Returns:
        dict with file_path, filename, saved_at.
    """
    history_dir = _get_history_dir(data_root)

    # Generate filename: YYYY-MM-DD_HH-MM_<sanitized_kp>.md
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M")
    sanitized_kp = _sanitize_filename(knowledge_point)
    filename = f"{timestamp}_{sanitized_kp}.md"
    file_path = history_dir / filename

    # Build Markdown content with metadata header
    metadata = (
        f"---\n"
        f"knowledge_point: {knowledge_point}\n"
        f"source: {source}\n"
        f"mastery_score: {mastery_score:.2f}\n"
        f"saved_at: {now.isoformat()}\n"
        f"---\n\n"
    )

    # Write file
    file_path.write_text(metadata + content, encoding="utf-8")
    logger.info("Saved learn content: %s", file_path)

    return {
        "file_path": str(file_path),
        "filename": filename,
        "saved_at": now.isoformat(),
        "knowledge_point": knowledge_point,
    }


def list_learn_history(data_root: str | None = None) -> list[dict[str, Any]]:
    """List all saved learning materials.

    Returns:
        List of dicts with filename, knowledge_point, saved_at, file_path.
    """
    history_dir = _get_history_dir(data_root)
    results = []

    for file_path in sorted(history_dir.glob("*.md"), reverse=True):
        try:
            # Read first few lines to extract metadata
            content = file_path.read_text(encoding="utf-8")
            metadata = _parse_metadata(content)

            results.append({
                "filename": file_path.name,
                "file_path": str(file_path),
                "knowledge_point": metadata.get("knowledge_point", file_path.stem),
                "source": metadata.get("source", "unknown"),
                "mastery_score": float(metadata.get("mastery_score", 0.5)),
                "saved_at": metadata.get("saved_at", ""),
            })
        except Exception as exc:
            logger.warning("Failed to read learn history file %s: %s", file_path, exc)

    return results


def get_learn_content(filename: str, data_root: str | None = None) -> dict[str, Any] | None:
    """Get the content of a specific learning material.

    Args:
        filename: The filename to retrieve.

    Returns:
        dict with content and metadata, or None if not found.
    """
    history_dir = _get_history_dir(data_root)
    file_path = history_dir / filename

    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
        metadata = _parse_metadata(content)

        # Remove metadata header from content
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()

        return {
            "filename": filename,
            "content": body,
            "metadata": metadata,
        }
    except Exception as exc:
        logger.warning("Failed to read learn content %s: %s", filename, exc)
        return None


def _parse_metadata(content: str) -> dict[str, str]:
    """Parse YAML-like metadata from the beginning of a Markdown file."""
    metadata = {}

    if not content.startswith("---"):
        return metadata

    try:
        # Find the closing ---
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return metadata

        metadata_str = content[3:end_idx].strip()

        # Simple YAML parser for key: value pairs
        for line in metadata_str.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
    except Exception:
        pass

    return metadata


def delete_learn_content(filename: str, data_root: str | None = None) -> bool:
    """Delete a specific learning material.

    Args:
        filename: The filename to delete.

    Returns:
        True if deleted, False if not found.
    """
    history_dir = _get_history_dir(data_root)
    file_path = history_dir / filename

    if file_path.exists():
        file_path.unlink()
        logger.info("Deleted learn content: %s", file_path)
        return True

    return False
