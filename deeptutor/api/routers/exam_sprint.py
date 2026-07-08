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
    onboarding_completed: bool = Field(False, description="Whether onboarding wizard is completed")
    diagnosis_completed: bool = Field(False, description="Whether diagnosis quiz is completed")
    kb_name: str = Field("", description="Associated knowledge base name")


@router.post("/state")
async def save_exam_state(req: ExamStateRequest) -> dict[str, Any]:
    """Save exam state (cold start setup)."""
    from deeptutor.exam.state import update_state

    return update_state(
        exam_name=req.exam_name,
        exam_date=req.exam_date,
        daily_budget_minutes=req.daily_budget_minutes,
        onboarding_completed=req.onboarding_completed,
        diagnosis_completed=req.diagnosis_completed,
        kb_name=req.kb_name,
    )


# ---------------------------------------------------------------------------
# Mastery endpoints
# ---------------------------------------------------------------------------


@router.get("/mastery")
async def get_mastery() -> list[dict[str, Any]]:
    """Return all mastery entries for the Exam Sprint dashboard."""
    from deeptutor.exam.profile import load_mastery

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
    from deeptutor.exam.profile import update_mastery_score

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
    from deeptutor.exam.profile import load_mastery
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

    # 5. Return content (save is user-initiated via /learn/save)
    return {
        "knowledge_point": req.knowledge_point,
        "content": content,
        "source": source,
        "mastery_score": mastery_score,
    }


# ---------------------------------------------------------------------------
# Learn history endpoints
# ---------------------------------------------------------------------------


class LearnSaveRequest(BaseModel):
    knowledge_point: str = Field(..., min_length=1, description="Knowledge point")
    content: str = Field(..., min_length=1, description="Markdown content to save")
    source: str = Field("llm", description="Content source: rag or llm")
    mastery_score: float = Field(0.5, description="Mastery score at generation time")


@router.post("/learn/save")
async def save_learn_content(req: LearnSaveRequest) -> dict[str, Any]:
    """Manually save learning content to history."""
    from deeptutor.exam.learn_history import save_learn_content as save_content

    save_result = save_content(
        knowledge_point=req.knowledge_point,
        content=req.content,
        source=req.source,
        mastery_score=req.mastery_score,
    )
    return save_result


@router.get("/learn/history")
async def list_learn_history() -> dict[str, Any]:
    """List all saved learning materials."""
    from deeptutor.exam.learn_history import list_learn_history as list_history

    history = list_history()
    return {
        "items": history,
        "count": len(history),
    }


@router.get("/learn/history/{filename}")
async def get_learn_content(filename: str) -> dict[str, Any]:
    """Get a specific learning material by filename."""
    from deeptutor.exam.learn_history import get_learn_content as get_content

    result = get_content(filename)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Learn content not found: {filename}")

    return result


@router.delete("/learn/history/{filename}")
async def delete_learn_content(filename: str) -> dict[str, str]:
    """Delete a specific learning material."""
    from deeptutor.exam.learn_history import delete_learn_content as delete_content

    deleted = delete_content(filename)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Learn content not found: {filename}")

    return {"status": "deleted", "filename": filename}


# ---------------------------------------------------------------------------
# Profile endpoint — full user profile (system + user facing)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Diagnosis endpoints — initial assessment during cold start
# ---------------------------------------------------------------------------


class DiagnosisGenerateRequest(BaseModel):
    exam_name: str = Field(..., min_length=1, description="Exam name for context")
    kb_name: str = Field("", description="Knowledge base name for RAG-scoped generation")
    language: str = Field("zh", description="Language code")


@router.post("/diagnosis/generate")
async def generate_diagnosis(req: DiagnosisGenerateRequest) -> list[dict[str, Any]]:
    """Generate diagnostic assessment questions via single LLM call.

    Unlike generate_questions which uses the full QuestionPipeline (explore→plan→quiz),
    diagnosis uses a lightweight single-call approach for faster response.
    The LLM determines question count dynamically based on exam scope.
    """
    from deeptutor.services.llm import get_llm_client

    # RAG context for diagnosis
    rag_context = ""
    if req.kb_name.strip():
        try:
            from deeptutor.multi_user.knowledge_access import resolve_for_rag
            from deeptutor.services.rag.service import RAGService

            resource = resolve_for_rag(req.kb_name)
            if resource is not None:
                rag_service = RAGService(kb_base_dir=str(resource.base_dir))
                rag_result = await rag_service.search(
                    query=f"{req.exam_name} 核心知识点诊断",
                    kb_name=resource.name,
                )
                answer = rag_result.get("answer") or rag_result.get("content") or ""
                if answer:
                    rag_context = f"\n\nRelevant knowledge base context:\n{answer}"
        except Exception as exc:
            logger.warning("RAG search failed for diagnosis kb=%s: %s", req.kb_name, exc)

    system_prompt = (
        "You are an exam diagnostic assessment generator. "
        "Generate diagnostic questions to assess a student's understanding of the exam topics. "
        "Return a JSON array of questions. Each question must have: "
        "question_id (string), question (string), question_type ('choice'|'short_answer'), "
        "options (object with key-value pairs, or null for short_answer), "
        "correct_answer (string), explanation (string), difficulty ('easy'|'medium'|'hard'), "
        "knowledge_point (string indicating which topic it tests). "
        "Generate exactly 5 questions covering different topics. "
        "Return ONLY the JSON array, no other text."
    )

    user_prompt = (
        f"Generate a diagnostic assessment for the exam: {req.exam_name}\n"
        f"Cover core knowledge points across all major chapters/topics.\n"
        f"The goal is to assess the student's current understanding level.\n"
    )
    if rag_context:
        user_prompt += f"\nReference material from knowledge base:\n{rag_context}\n"
    user_prompt += "\nReturn a JSON array of diagnostic questions."

    llm = get_llm_client()
    try:
        import json as _json
        import re as _re

        raw_response = await llm.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        logger.info("Diagnosis LLM response length: %d chars", len(raw_response or ""))
        logger.info("Diagnosis LLM response first 500: %s", (raw_response or "")[:500])

        # Extract JSON array from response
        text = raw_response.strip()
        if not text:
            logger.error("Diagnosis LLM returned empty response")
            raise ValueError("LLM returned empty response")

        # Try 1: direct parse
        try:
            questions = _json.loads(text)
        except _json.JSONDecodeError as e1:
            logger.warning("JSON direct parse failed: %s", e1)
            # Try 2: extract from markdown code block
            code_block = _re.search(r"```(?:json)?\s*\n(.*?)```", text, _re.DOTALL)
            if code_block:
                text = code_block.group(1).strip()
                try:
                    questions = _json.loads(text)
                except _json.JSONDecodeError as e2:
                    logger.warning("JSON code block parse failed: %s", e2)
                    raise ValueError(f"Could not parse JSON from code block ({len(text)} chars): {e2}")
            else:
                # Try 3: find the first [ ... ] array
                arr_match = _re.search(r"\[.*\]", text, _re.DOTALL)
                if arr_match:
                    try:
                        questions = _json.loads(arr_match.group())
                    except _json.JSONDecodeError as e3:
                        logger.warning("JSON array parse failed: %s", e3)
                        raise ValueError(f"Could not parse extracted array ({len(arr_match.group())} chars): {e3}")
                else:
                    logger.error("No JSON array found in response. Full text (%d chars): %s", len(text), text[:1000])
                    raise ValueError(f"Could not extract JSON array from response ({len(text)} chars)")

        if not isinstance(questions, list):
            raise ValueError("Response is not a JSON array")

        # Normalize fields
        normalized: list[dict[str, Any]] = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict) or "question" not in q:
                continue
            normalized.append({
                "question_id": q.get("question_id", f"diag_{i+1}"),
                "question": q["question"],
                "question_type": q.get("question_type", "short_answer"),
                "options": q.get("options"),
                "correct_answer": q.get("correct_answer", ""),
                "explanation": q.get("explanation", ""),
                "difficulty": q.get("difficulty", "medium"),
                "knowledge_point": q.get("knowledge_point", ""),
            })

        if not normalized:
            raise ValueError("No valid questions in response")

        return normalized

    except Exception as exc:
        logger.exception("Diagnosis generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Diagnosis generation failed: {type(exc).__name__}: {exc}",
        )


class DiagnosisSubmitRequest(BaseModel):
    exam_name: str = Field(..., min_length=1, description="Exam name")
    answers: list[dict[str, Any]] = Field(..., description="List of answer records")
    # Each answer: {question_id, question, correct_answer, user_answer, is_correct, error_type, knowledge_point}


@router.post("/diagnosis/submit")
async def submit_diagnosis(req: DiagnosisSubmitRequest) -> dict[str, Any]:
    """Submit diagnosis answers and initialize the user profile.

    Aggregates results by knowledge point, calculates initial scores,
    and writes to profile.json (first-time initialization, not EMA).
    """
    from deeptutor.exam.profile import init_from_diagnosis

    # Calculate overall score
    total = len(req.answers)
    correct = sum(1 for a in req.answers if a.get("is_correct"))
    overall_score = round(correct / total, 3) if total > 0 else 0.0

    # Sort knowledge points by score to find weak/strong
    kp_scores: dict[str, list[bool]] = {}
    for a in req.answers:
        kp = a.get("knowledge_point", "unknown")
        if kp not in kp_scores:
            kp_scores[kp] = []
        kp_scores[kp].append(a.get("is_correct", False))

    kp_avg = {kp: sum(v) / len(v) for kp, v in kp_scores.items() if v}
    weak_points = [kp for kp, avg in sorted(kp_avg.items(), key=lambda x: x[1]) if avg < 0.6]
    strong_points = [kp for kp, avg in sorted(kp_avg.items(), key=lambda x: -x[1]) if avg >= 0.8]

    diagnosis_result = {
        "total_questions": total,
        "questions": req.answers,
        "overall_score": overall_score,
        "weak_points": weak_points,
        "strong_points": strong_points,
    }

    profile = init_from_diagnosis(req.exam_name, diagnosis_result)

    # Save wrong questions to practice history
    from deeptutor.exam.practice_history import save_wrong_question

    wrong_count = 0
    for a in req.answers:
        if not a.get("is_correct"):
            save_wrong_question(a, source="diagnosis")
            wrong_count += 1

    # Auto-generate task list after diagnosis
    from deeptutor.exam.tasks import generate_tasks_from_diagnosis, save_tasks
    from deeptutor.exam.state import load_state
    from datetime import datetime, timezone

    tasks_data = {"tasks": [], "total_tasks": 0, "completed_tasks": 0}
    try:
        state = load_state()
        exam_date = state.get("exam_date", "")
        if exam_date:
            exam_dt = datetime.fromisoformat(exam_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_remaining = max(1, (exam_dt - now).days)
            daily_hours = state.get("daily_budget_minutes", 120) / 60

            tasks_data = generate_tasks_from_diagnosis(
                knowledge_points=profile.get("knowledge_points", []),
                days_remaining=days_remaining,
                daily_hours=daily_hours,
            )
            save_tasks(tasks_data)
    except Exception as e:
        logger.warning("Failed to generate tasks after diagnosis: %s", e)

    return {
        "status": "ok",
        "overall_score": overall_score,
        "total_questions": total,
        "correct": correct,
        "wrong_saved": wrong_count,
        "weak_points": weak_points,
        "strong_points": strong_points,
        "knowledge_points": profile.get("knowledge_points", []),
        "tasks_generated": tasks_data.get("total_tasks", 0),
    }


# ---------------------------------------------------------------------------
# Profile endpoint — full user profile (system + user facing)
# ---------------------------------------------------------------------------


@router.get("/profile")
async def get_profile() -> dict[str, Any]:
    """Return the full user profile (knowledge_points + diagnosis)."""
    from deeptutor.exam.profile import load_profile

    return load_profile()


@router.get("/diagnosis/report")
async def get_diagnosis_report() -> dict[str, Any]:
    """Return the diagnosis report from profile.

    Contains: completed_at, total_questions, correct, overall_score,
    questions (with user answers), weak_points, strong_points.
    """
    from deeptutor.exam.profile import load_profile

    profile = load_profile()
    diagnosis = profile.get("diagnosis")
    if diagnosis is None:
        raise HTTPException(status_code=404, detail="No diagnosis report found")
    return diagnosis


# ---------------------------------------------------------------------------
# State reset — destructive, clears all exam data
# ---------------------------------------------------------------------------


@router.post("/state/reset")
async def reset_exam_state() -> dict[str, str]:
    """Reset all exam state to defaults.

    Deletes: state.json, profile.json, learn_history/, practice_history.json, tasks.json.
    Requires user confirmation on the frontend before calling.
    """
    from deeptutor.exam.state import reset_state
    from deeptutor.exam.tasks import reset_tasks

    reset_state()
    reset_tasks()
    return {"status": "ok", "message": "All exam data has been reset"}


# ---------------------------------------------------------------------------
# Task list endpoints — daily tasks generated from weak points
# ---------------------------------------------------------------------------


@router.get("/tasks")
async def get_tasks() -> dict[str, Any]:
    """Get today's task list.

    Returns tasks generated from diagnosis weak points + time pressure.
    If no tasks exist, returns empty list.
    """
    from deeptutor.exam.tasks import load_tasks

    return load_tasks()


@router.post("/task/complete")
async def complete_task_endpoint(task_id: str) -> dict[str, Any]:
    """Mark a task as completed.

    Updates task status and returns the updated task list.
    """
    from deeptutor.exam.tasks import complete_task

    result = complete_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return result


@router.post("/task/generate")
async def generate_tasks_endpoint() -> dict[str, Any]:
    """Generate initial task list from diagnosis knowledge points.

    Called after cold start diagnosis completes.
    Uses PlanBuilder logic to create prioritized tasks.
    """
    from deeptutor.exam.tasks import generate_tasks_from_diagnosis, save_tasks
    from deeptutor.exam.profile import load_profile
    from deeptutor.exam.state import load_state

    profile = load_profile()
    state = load_state()

    knowledge_points = profile.get("knowledge_points", [])
    if not knowledge_points:
        raise HTTPException(status_code=400, detail="No knowledge points found. Complete diagnosis first.")

    exam_date = state.get("exam_date", "")
    if not exam_date:
        raise HTTPException(status_code=400, detail="No exam date set.")

    # Calculate days remaining
    from datetime import datetime, timezone
    try:
        exam_dt = datetime.fromisoformat(exam_date.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_remaining = max(1, (exam_dt - now).days)
    except Exception:
        days_remaining = 14  # fallback

    daily_hours = state.get("daily_budget_minutes", 120) / 60

    tasks_data = generate_tasks_from_diagnosis(
        knowledge_points=knowledge_points,
        days_remaining=days_remaining,
        daily_hours=daily_hours,
    )
    save_tasks(tasks_data)

    return tasks_data


# ---------------------------------------------------------------------------
# SSE streaming diagnosis — one question at a time
# ---------------------------------------------------------------------------


@router.post("/diagnosis/stream")
async def stream_diagnosis(req: DiagnosisGenerateRequest):
    """Stream diagnostic questions one-by-one via Server-Sent Events.

    Each question is generated in a separate LLM call for reliability.
    Events:
      - question: {index, total, question: {...}}
      - complete: {total, message}
      - error: {message}
    """
    from fastapi.responses import StreamingResponse
    from deeptutor.services.llm import get_llm_client
    import json as _json

    total_questions = 5

    async def event_generator():
        llm = get_llm_client()
        generated = 0

        for i in range(total_questions):
            system_prompt = (
                "You are an exam diagnostic question generator. "
                "Generate exactly ONE diagnostic question. "
                "Return a JSON object (not array) with these EXACT fields: "
                "question_id (string like 'CN_001'), "
                "question (string - the question text), "
                "question_type ('choice' for multiple choice, 'short_answer' for fill-in), "
                "options (object with A/B/C/D keys and Chinese text values, or null for short_answer), "
                "correct_answer (string - the correct option letter like 'A'/'B'/'C'/'D'), "
                "explanation (string - detailed explanation in Chinese), "
                "difficulty ('easy'|'medium'|'hard'), "
                "knowledge_point (string - the specific topic name in Chinese like 'TCP拥塞控制' or 'IP子网划分'). "
                "IMPORTANT: knowledge_point MUST be a non-empty Chinese string describing the topic. "
                "Return ONLY the JSON object, no other text."
            )

            user_prompt = (
                f"Generate diagnostic question {i+1}/{total_questions} for exam: {req.exam_name}\n"
                f"Each question must cover a DIFFERENT knowledge point (e.g., TCP, IP, subnet, routing, etc.).\n"
                f"Vary difficulty levels across questions.\n"
                "Return ONLY the JSON object with all required fields."
            )

            try:
                raw_response = await llm.complete(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                )

                logger.info("SSE diagnosis Q%d response length: %d", i+1, len(raw_response or ""))

                text = (raw_response or "").strip()
                if not text:
                    logger.warning("SSE diagnosis Q%d empty response, retrying", i+1)
                    # Retry once
                    raw_response = await llm.complete(
                        prompt=user_prompt + "\nIMPORTANT: Return valid JSON only.",
                        system_prompt=system_prompt,
                    )
                    text = (raw_response or "").strip()

                if not text:
                    yield f"event: error\ndata: {_json.dumps({'message': f'Question {i+1} returned empty'})}\n\n"
                    continue

                # Parse JSON (try direct, then code block, then regex)
                question = None
                try:
                    question = _json.loads(text)
                except _json.JSONDecodeError:
                    import re
                    code_block = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
                    if code_block:
                        try:
                            question = _json.loads(code_block.group(1).strip())
                        except _json.JSONDecodeError:
                            pass
                    if question is None:
                        obj_match = re.search(r"\{.*\}", text, re.DOTALL)
                        if obj_match:
                            try:
                                question = _json.loads(obj_match.group())
                            except _json.JSONDecodeError:
                                pass

                if not isinstance(question, dict) or "question" not in question:
                    logger.warning("SSE diagnosis Q%d invalid format: %s", i+1, text[:200])
                    yield f"event: error\ndata: {_json.dumps({'message': f'Question {i+1} invalid format'})}\n\n"
                    continue

                # Ensure question_id
                if not question.get("question_id"):
                    question["question_id"] = f"diag_{i+1}"

                # Map knowledge_point to concentration for frontend compatibility
                if question.get("knowledge_point") and not question.get("concentration"):
                    question["concentration"] = question["knowledge_point"]

                generated += 1
                event_data = _json.dumps({
                    "index": i,
                    "total": total_questions,
                    "question": question,
                }, ensure_ascii=False)
                yield f"event: question\ndata: {event_data}\n\n"

            except Exception as exc:
                logger.exception("SSE diagnosis Q%d failed: %s", i+1, exc)
                yield f"event: error\ndata: {_json.dumps({'message': str(exc)})}\n\n"

        # Signal completion
        yield f"event: complete\ndata: {_json.dumps({'total': generated, 'message': 'Diagnosis complete'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Practice history endpoints — wrong questions for review
# ---------------------------------------------------------------------------


@router.get("/practice/history")
async def list_practice_history(knowledge_point: str | None = None) -> dict[str, Any]:
    """List practice history (wrong questions), optionally filtered by knowledge point."""
    from deeptutor.exam.practice_history import list_practice_history as list_history

    items = list_history(knowledge_point=knowledge_point)
    return {"items": items, "count": len(items)}


@router.get("/practice/history/{record_id}")
async def get_practice_history(record_id: str) -> dict[str, Any]:
    """Get a specific practice history record."""
    from deeptutor.exam.practice_history import get_practice_history as get_history

    result = get_history(record_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Practice record not found: {record_id}")
    return result


@router.delete("/practice/history/{record_id}")
async def delete_practice_history(record_id: str) -> dict[str, str]:
    """Delete a specific practice history record."""
    from deeptutor.exam.practice_history import delete_practice_history as delete_history

    deleted = delete_history(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Practice record not found: {record_id}")
    return {"status": "deleted", "id": record_id}


class PracticeSaveWrongBatchRequest(BaseModel):
    questions: list[dict[str, Any]] = Field(
        ..., description="List of wrong question records to save"
    )
    source: str = Field("practice", description="Source identifier (practice/diagnosis)")


@router.post("/practice/save-wrong-batch")
async def save_wrong_questions_batch(req: PracticeSaveWrongBatchRequest) -> dict[str, Any]:
    """Batch save wrong questions to practice history.

    Used by daily practice to automatically save wrong answers.
    """
    from deeptutor.exam.practice_history import save_wrong_question

    saved_count = 0
    for q in req.questions:
        save_wrong_question(q, source=req.source)
        saved_count += 1

    return {
        "status": "ok",
        "saved_count": saved_count,
        "source": req.source,
    }
