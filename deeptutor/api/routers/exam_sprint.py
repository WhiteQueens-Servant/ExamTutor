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
# Exam state endpoints (cold start)
# ---------------------------------------------------------------------------


@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Return the current exam state (name, date, phase, etc.)."""
    from deeptutor.exam.state import load_state

    return load_state()


class ExamStateRequest(BaseModel):
    exam_name: str = Field(..., min_length=1, description="Exam name (e.g. '信号与系统 期末考试')")
    exam_date: str = Field(..., description="Exam date in YYYY-MM-DD format")
    daily_budget_minutes: int = Field(120, ge=10, le=480, description="Daily study budget in minutes")


@router.post("/state")
async def save_exam_state(req: ExamStateRequest) -> dict[str, Any]:
    """Save exam state (cold start setup)."""
    from deeptutor.exam.state import update_state

    return update_state(
        exam_name=req.exam_name,
        exam_date=req.exam_date,
        daily_budget_minutes=req.daily_budget_minutes,
    )


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


# ---------------------------------------------------------------------------
# Learn endpoint — generate learning material for a knowledge point
# ---------------------------------------------------------------------------


class LearnRequest(BaseModel):
    knowledge_point: str = Field(..., min_length=1, description="Knowledge point to learn")
    kb_name: str = Field("", description="Knowledge base name for RAG retrieval. Empty = LLM only.")
    language: str = Field("zh", description="Language code")


@router.post("/learn")
async def generate_learn_content(req: LearnRequest) -> dict[str, Any]:
    """Generate learning material for a knowledge point.

    Pipeline:
    1. Read mastery score for context
    2. RAG search (if kb_name provided) for reference material
    3. LLM generates stage-aware, mastery-calibrated learning content
    4. Returns Markdown content + source info
    """
    from deeptutor.exam.mastery import load_mastery
    from deeptutor.services.llm import get_llm_client

    # 1. Read mastery for this knowledge point
    mastery_entries = load_mastery()
    mastery_score = 0.5  # default
    for entry in mastery_entries:
        if entry.get("knowledge_point") == req.knowledge_point:
            mastery_score = entry.get("score", 0.5)
            break

    # 2. RAG search for reference material
    rag_context = ""
    source = "llm"
    if req.kb_name.strip():
        try:
            from deeptutor.multi_user.knowledge_access import resolve_for_rag
            from deeptutor.services.rag.service import RAGService

            resource = resolve_for_rag(req.kb_name)
            if resource is not None:
                rag_service = RAGService(kb_base_dir=str(resource.base_dir))
                rag_result = await rag_service.search(
                    query=req.knowledge_point,
                    kb_name=resource.name,
                )
                answer = rag_result.get("answer") or rag_result.get("content") or ""
                if answer:
                    rag_context = answer
                    source = "rag"
                    logger.info("RAG retrieved %d chars for learn: %s", len(answer), req.knowledge_point)
        except Exception as exc:
            logger.warning("RAG search failed for learn kb=%s: %s — using LLM only", req.kb_name, exc)

    # 3. Build prompt with stage/mastery context
    if mastery_score < 0.3:
        depth_instruction = "从基础概念讲起，详细解释定义和原理，配合简单例题。"
    elif mastery_score < 0.5:
        depth_instruction = "侧重概念理解和核心公式推导，配合中等难度例题。"
    elif mastery_score < 0.7:
        depth_instruction = "侧重进阶应用和易错点辨析，配合综合例题。"
    else:
        depth_instruction = "简要回顾核心要点，侧重高频考点和易混淆概念。"

    system_prompt = (
        "你是一位经验丰富的备考辅导老师。"
        "请用 Markdown 格式生成学习材料，支持 LaTeX 数学公式（用 $...$ 包裹）。"
        "内容结构：概念解释 → 核心公式 → 典型例题 → 要点总结。"
    )

    user_prompt = f"请为学生生成「{req.knowledge_point}」的学习材料。\n\n"
    user_prompt += f"【学生掌握度】{mastery_score:.0%}\n"
    user_prompt += f"【讲解深度】{depth_instruction}\n\n"

    if rag_context:
        user_prompt += f"【参考材料】（来自知识库）\n{rag_context}\n\n"
        user_prompt += "请基于以上参考材料，为学生整理学习内容。如果参考材料不足，可补充通用知识。\n"
    else:
        user_prompt += "无知识库参考，请基于通用知识生成学习材料。\n"

    user_prompt += "\n输出纯 Markdown，包含公式和例题。"

    # 4. Call LLM
    llm = get_llm_client()
    try:
        content = await llm.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.exception("LLM failed for learn: %s", req.knowledge_point)
        raise HTTPException(
            status_code=500,
            detail=f"Learn generation failed: {type(exc).__name__}: {exc}",
        )

    return {
        "knowledge_point": req.knowledge_point,
        "content": content,
        "source": source,
        "mastery_score": mastery_score,
    }
