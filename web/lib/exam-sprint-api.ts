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
  onboarding_completed: boolean;
  diagnosis_completed: boolean;
  kb_name: string;
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
  onboarding_completed?: boolean;
  diagnosis_completed?: boolean;
  kb_name?: string;
}): Promise<ExamState> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/state"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      exam_name: params.exam_name,
      exam_date: params.exam_date,
      daily_budget_minutes: params.daily_budget_minutes ?? 120,
      onboarding_completed: params.onboarding_completed ?? false,
      diagnosis_completed: params.diagnosis_completed ?? false,
      kb_name: params.kb_name ?? "",
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

// ---------------------------------------------------------------------------
// Profile (full user profile)
// ---------------------------------------------------------------------------

export interface KnowledgePoint {
  name: string;
  chapter: string;
  score: number;
  total_questions: number;
  correct: number;
  error_types: string[];
  last_practiced: string;
  practice_count: number;
  last_surface: string;
}

export interface DiagnosisReport {
  completed_at: string;
  total_questions: number;
  correct: number;
  overall_score: number;
  questions: Array<{
    question_id: string;
    question: string;
    correct_answer: string;
    user_answer: string;
    is_correct: boolean;
    error_type: string;
    knowledge_point: string;
  }>;
  weak_points: string[];
  strong_points: string[];
}

export interface UserProfile {
  exam_name: string;
  created_at: string;
  last_updated: string;
  knowledge_points: KnowledgePoint[];
  diagnosis: DiagnosisReport | null;
}

/**
 * Fetch the full user profile (knowledge_points + diagnosis).
 */
export async function fetchProfile(): Promise<UserProfile> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/profile"));
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch profile (${res.status}): ${detail}`);
  }
  return await res.json();
}

// ---------------------------------------------------------------------------
// State reset
// ---------------------------------------------------------------------------

/**
 * Reset all exam state (requires user confirmation before calling).
 */
export async function resetExamState(): Promise<void> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/state/reset"), {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to reset state (${res.status}): ${detail}`);
  }
}

// ---------------------------------------------------------------------------
// Diagnosis (cold start assessment)
// ---------------------------------------------------------------------------

/**
 * Generate diagnostic assessment questions.
 * LLM determines question count dynamically based on exam scope.
 */
export async function generateDiagnosis(params: {
  exam_name: string;
  kb_name?: string;
  language?: string;
}): Promise<QuizQuestion[]> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/diagnosis/generate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      exam_name: params.exam_name,
      kb_name: params.kb_name ?? "",
      language: params.language ?? "zh",
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Diagnosis generation failed (${res.status}): ${detail}`);
  }
  return await res.json();
}

export interface DiagnosisSubmitResult {
  status: string;
  overall_score: number;
  total_questions: number;
  correct: number;
  weak_points: string[];
  strong_points: string[];
  knowledge_points: KnowledgePoint[];
}

/**
 * Submit diagnosis answers and initialize the user profile.
 */
export async function submitDiagnosis(params: {
  exam_name: string;
  answers: Array<{
    question_id: string;
    question: string;
    correct_answer: string;
    user_answer: string;
    is_correct: boolean;
    error_type: string;
    knowledge_point: string;
  }>;
}): Promise<DiagnosisSubmitResult> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/diagnosis/submit"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      exam_name: params.exam_name,
      answers: params.answers,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Diagnosis submit failed (${res.status}): ${detail}`);
  }
  return await res.json();
}
