/**
 * Exam Sprint API client — quiz question generation + learn content.
 */

import type { QuizQuestion } from "./quiz-types";
import { apiFetch, apiUrl } from "./api";

export interface GenerateQuestionsParams {
  topic: string;
  num_questions?: number;
  difficulty?: string;
  language?: string;
  kb_name?: string;
}

/**
 * Generate quiz questions for a given topic via the backend QuestionPipeline.
 *
 * @returns Array of QuizQuestion objects compatible with QuizPreview / QuizViewer.
 */
export async function generateExamQuestions(
  params: GenerateQuestionsParams,
): Promise<QuizQuestion[]> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/generate-questions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic: params.topic,
      num_questions: params.num_questions ?? 3,
      difficulty: params.difficulty ?? "",
      language: params.language ?? "zh",
      kb_name: params.kb_name ?? "",
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Question generation failed (${res.status}): ${detail}`);
  }

  const data: QuizQuestion[] = await res.json();
  return data;
}

// ---------------------------------------------------------------------------
// Exam state (cold start)
// ---------------------------------------------------------------------------

export interface ExamState {
  exam_name: string;
  exam_date: string;
  phase: string;
  streak: number;
  last_active: string;
  daily_budget_minutes: number;
  total_tasks_today: number;
  completed_tasks_today: number;
}

/**
 * Fetch the current exam state.
 */
export async function fetchExamState(): Promise<ExamState> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/state"));
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch exam state (${res.status}): ${detail}`);
  }
  return await res.json();
}

/**
 * Save exam state (cold start setup).
 */
export async function saveExamState(params: {
  exam_name: string;
  exam_date: string;
  daily_budget_minutes?: number;
}): Promise<ExamState> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/state"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      exam_name: params.exam_name,
      exam_date: params.exam_date,
      daily_budget_minutes: params.daily_budget_minutes ?? 120,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to save exam state (${res.status}): ${detail}`);
  }
  return await res.json();
}

// ---------------------------------------------------------------------------
// Learn content generation
// ---------------------------------------------------------------------------

export interface LearnContentParams {
  knowledge_point: string;
  kb_name?: string;
  language?: string;
}

export interface LearnContentResult {
  knowledge_point: string;
  content: string;       // Markdown
  source: "rag" | "llm";
  mastery_score: number;
}

/**
 * Generate learning material for a knowledge point via RAG + LLM.
 */
export async function generateLearnContent(
  params: LearnContentParams,
): Promise<LearnContentResult> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/learn"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      knowledge_point: params.knowledge_point,
      kb_name: params.kb_name ?? "",
      language: params.language ?? "zh",
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Learn generation failed (${res.status}): ${detail}`);
  }

  return await res.json();
}
