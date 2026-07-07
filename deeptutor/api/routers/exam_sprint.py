"""Exam Sprint API — quiz question generation for the Exam Sprint dashboard."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateQuestionsRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Knowledge point topic to generate questions for")
    num_questions: int = Field(3, ge=1, le=20, description="Number of questions to generate")
    difficulty: str = Field("", description="Difficulty level: easy, medium, hard, or auto")
    language: str = Field("zh", description="Language code for question generation")
    kb_name: str = Field("", description="Knowledge base name for RAG-scoped retrieval. Empty = no RAG.")


@router.post("/generate-questions")
async def generate_questions(req: GenerateQuestionsRequest) -> list[dict[str, Any]]:
    """Generate quiz questions for a given topic via QuestionPipeline.

    Returns a list of QuizQuestion objects compatible with the frontend
    QuizPreview / QuizViewer components.
    """
    from deeptutor.agents.question.pipeline import QuestionPipeline
    from deeptutor.agents.question.request_config import build_question_runtime_config
    from deeptutor.core.context import UnifiedContext
    from deeptutor.core.stream_bus import StreamBus
    from deeptutor.services.config import load_config_with_main

    session_id = str(uuid.uuid4())

    # RAG-scoped retrieval: search the selected KB for relevant context
    rag_context = ""
    if req.kb_name.strip():
        try:
            from deeptutor.multi_user.knowledge_access import resolve_for_rag
            from deeptutor.services.rag.service import RAGService

            resource = resolve_for_rag(req.kb_name)
            if resource is not None:
                rag_service = RAGService(kb_base_dir=str(resource.base_dir))
                rag_result = await rag_service.search(
                    query=req.topic,
                    kb_name=resource.name,
                )
                answer = rag_result.get("answer") or rag_result.get("content") or ""
                if answer:
                    rag_context = f"\n\nRelevant knowledge base context:\n{answer}"
                    logger.info("RAG retrieved %d chars for topic=%s", len(answer), req.topic)
            else:
                logger.warning("KB '%s' not accessible, proceeding without RAG", req.kb_name)
        except Exception as exc:
            logger.warning("RAG search failed for kb=%s: %s — falling back to LLM only", req.kb_name, exc)

    # Build the user message, optionally including RAG context
    user_message = (
        f"Generate {req.num_questions} practice questions about: {req.topic}. "
        f"Focus on testing understanding of core concepts."
        f"{rag_context}"
    )

    context = UnifiedContext(
        session_id=session_id,
        user_message=user_message,
        active_capability="exam_sprint",
        language=req.language,
    )

    runtime_config = build_question_runtime_config(
        base_config=load_config_with_main("main.yaml"),
    )

    pipeline = QuestionPipeline(
        language=req.language,
        runtime_config=runtime_config,
    )

    stream = StreamBus()

    try:
        result_payload = await pipeline.run(
            context=context,
            user_message=user_message,
            num_questions=req.num_questions,
            difficulty=req.difficulty,
            stream=stream,
        )
    except Exception as exc:
        logger.exception("QuestionPipeline failed for topic=%s", req.topic)
        raise HTTPException(
            status_code=500,
            detail=f"Question generation failed: {type(exc).__name__}: {exc}",
        )

    # Extract QuizQuestion[] from the result envelope
    summary = result_payload.get("summary", {}) if isinstance(result_payload, dict) else {}
    results = summary.get("results", []) if isinstance(summary, dict) else []

    questions: list[dict[str, Any]] = []
    for item in results:
        qa_pair = item.get("qa_pair") if isinstance(item, dict) else None
        if not qa_pair or not isinstance(qa_pair, dict):
            continue
        questions.append({
            "question_id": qa_pair.get("question_id", ""),
            "question": qa_pair.get("question", ""),
            "question_type": qa_pair.get("question_type", "short_answer"),
            "options": qa_pair.get("options"),
            "correct_answer": qa_pair.get("correct_answer", ""),
            "explanation": qa_pair.get("explanation", ""),
            "difficulty": qa_pair.get("difficulty", ""),
            "concentration": qa_pair.get("concentration", ""),
        })

    if not questions:
        raise HTTPException(
            status_code=502,
            detail="Question pipeline returned no questions. Check LLM configuration.",
        )

    return questions


# ---------------------------------------------------------------------------
# Mastery endpoints
# ---------------------------------------------------------------------------


@router.get("/mastery")
async def get_mastery() -> list[dict[str, Any]]:
    """Return all mastery entries for the Exam Sprint dashboard."""
    from deeptutor.exam.mastery import load_mastery

    return load_mastery()


class MasteryUpdateRequest(BaseModel):
    knowledge_point: str = Field(..., min_length=1, description="Knowledge point name")
    score: float = Field(..., ge=0.0, le=1.0, description="New score (0.0-1.0)")
    surface: str = Field("quiz", description="Source surface: notebook|quiz|chat|kb|book")


@router.post("/mastery/update")
async def update_mastery(req: MasteryUpdateRequest) -> list[dict[str, Any]]:
    """Update a mastery entry (exponential moving average blend).

    Returns the full updated mastery list.
    """
    from deeptutor.exam.mastery import update_mastery_score

    return update_mastery_score(
        knowledge_point=req.knowledge_point,
        new_score=req.score,
        surface=req.surface,
    )
