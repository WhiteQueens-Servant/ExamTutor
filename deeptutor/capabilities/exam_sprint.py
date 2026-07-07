"""
Exam Sprint Capability
======================

Time-pressure driven exam preparation pipeline.

V0: Empty shell — manifest only, ``run()`` is a no-op placeholder.
"""

from __future__ import annotations

import logging

from deeptutor.core.capability_protocol import BaseCapability, CapabilityManifest
from deeptutor.core.context import UnifiedContext
from deeptutor.core.stream_bus import StreamBus

logger = logging.getLogger(__name__)


class ExamSprintCapability(BaseCapability):
    """Exam preparation capability with time-pressure driven planning.

    Currently a placeholder. Real pipeline will be wired in Phase 4.
    """

    manifest = CapabilityManifest(
        name="exam_sprint",
        description="Exam preparation with time-pressure driven planning.",
        stages=["analysis", "planning", "execution", "review"],
        tools_used=["weak_point_ranker", "plan_builder", "time_pressure", "rag"],
        cli_aliases=["exam"],
        config_defaults={
            "mode": "sprint",  # sprint | practice | review
        },
    )

    async def run(self, context: UnifiedContext, stream: StreamBus) -> None:
        """Execute the exam sprint pipeline.

        V0: emits a single content event indicating the capability is registered
        but not yet wired.
        """
        logger.info("ExamSprintCapability.run() called — V0 placeholder")
        await stream.content(
            "Exam Sprint capability registered. Full pipeline coming in Phase 4.",
            source=self.manifest.name,
        )
