"""
Exam Sprint streaming helpers
==============================

Thin wrapper around ``StreamBus`` that fixes ``source="exam_sprint"`` and
defines exam-specific event metadata schemas.

Pattern reused from ``deeptutor.book.streaming.BookStream``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from deeptutor.core.stream import StreamEvent, StreamEventType
from deeptutor.core.stream_bus import StreamBus

SOURCE = "exam_sprint"

# Stage names used across the exam sprint pipeline
STAGE_ANALYSIS = "analysis"  # WeakPointRanker — mastery analysis
STAGE_PLANNING = "planning"  # PlanBuilder — task generation
STAGE_EXECUTION = "execution"  # Question pipeline / RAG study
STAGE_REVIEW = "review"  # Post-task mastery comparison


class ExamStream:
    """High-level helpers around a ``StreamBus`` for the ExamSprintCapability."""

    def __init__(self, bus: StreamBus) -> None:
        self.bus = bus

    @asynccontextmanager
    async def stage(self, name: str, metadata: dict[str, Any] | None = None):
        async with self.bus.stage(name, source=SOURCE, metadata=metadata or {}):
            yield

    async def content(
        self,
        text: str,
        stage: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.bus.content(text, source=SOURCE, stage=stage, metadata=metadata)

    async def thinking(
        self,
        text: str,
        stage: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.bus.thinking(text, source=SOURCE, stage=stage, metadata=metadata)

    async def progress(
        self,
        message: str,
        current: int = 0,
        total: int = 0,
        stage: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.bus.progress(
            message,
            current=current,
            total=total,
            source=SOURCE,
            stage=stage,
            metadata=metadata,
        )

    async def result(self, data: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
        await self.bus.result(data, source=SOURCE, metadata=metadata)

    async def error(
        self,
        message: str,
        stage: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.bus.error(message, source=SOURCE, stage=stage, metadata=metadata)

    async def emit(self, event_type: StreamEventType, **kwargs: Any) -> None:
        kwargs.setdefault("source", SOURCE)
        await self.bus.emit(StreamEvent(type=event_type, **kwargs))

    # ── Exam-specific events ─────────────────────────────────────────────

    async def exam_event(
        self,
        kind: str,
        data: dict[str, Any],
        stage: str = "",
    ) -> None:
        """Emit a custom 'exam' progress event using the PROGRESS channel.

        Frontend distinguishes by ``metadata.kind``::

            kind ∈ {
              "mastery_loaded", "tasks_generated", "question_ready",
              "answer_graded", "mastery_updated", "phase_switched", ...
            }
        """
        await self.bus.emit(
            StreamEvent(
                type=StreamEventType.PROGRESS,
                source=SOURCE,
                stage=stage,
                content=kind,
                metadata={"kind": kind, **data},
            )
        )


__all__ = [
    "ExamStream",
    "SOURCE",
    "STAGE_ANALYSIS",
    "STAGE_PLANNING",
    "STAGE_EXECUTION",
    "STAGE_REVIEW",
]
