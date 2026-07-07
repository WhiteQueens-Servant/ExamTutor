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
    user_message = (
        f"Generate {req.num_questions} practice questions about: {req.topic}. "
        f"Focus on testing understanding of core concepts."
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
