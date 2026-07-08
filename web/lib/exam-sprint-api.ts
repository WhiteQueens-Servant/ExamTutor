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

/**
 * SSE streaming diagnosis — generates questions one-by-one.
 * Calls callback for each question as it arrives.
 * Returns when all questions are generated or error occurs.
 */
export async function streamDiagnosis(params: {
  exam_name: string;
  kb_name?: string;
  language?: string;
  onQuestion: (question: QuizQuestion, index: number, total: number) => void;
  onError: (message: string) => void;
  onComplete: (total: number) => void;
}): Promise<void> {
  const res = await fetch(apiUrl("/api/v1/exam-sprint/diagnosis/stream"), {
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
    throw new Error(`Diagnosis stream failed (${res.status}): ${detail}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEventType = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process SSE events
    const lines = buffer.split("\n");
    buffer = lines.pop() || ""; // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        // Store event type, will be used when we find the data line
        currentEventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const eventData = line.slice(6);
        // When we have both event type and data, process the event
        if (currentEventType) {
          try {
            const parsed = JSON.parse(eventData);

            if (currentEventType === "question") {
              params.onQuestion(parsed.question, parsed.index, parsed.total);
            } else if (currentEventType === "complete") {
              params.onComplete(parsed.total);
            } else if (currentEventType === "error") {
              params.onError(parsed.message);
            }
          } catch (e) {
            console.error("Failed to parse SSE data:", e);
          }
          currentEventType = "";
        }
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Learn history
// ---------------------------------------------------------------------------

export interface LearnHistoryItem {
  filename: string;
  file_path: string;
  knowledge_point: string;
  source: string;
  mastery_score: number;
  saved_at: string;
}

export interface LearnHistoryResponse {
  items: LearnHistoryItem[];
  count: number;
}

export interface LearnContentResponse {
  filename: string;
  content: string;
  metadata: Record<string, string>;
}

export interface SaveLearnContentParams {
  knowledge_point: string;
  content: string;
  source?: string;
  mastery_score?: number;
}

/**
 * Manually save learning content to history.
 */
export async function saveLearnContent(
  params: SaveLearnContentParams,
): Promise<{ file_path: string; filename: string; saved_at: string }> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/learn/save"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      knowledge_point: params.knowledge_point,
      content: params.content,
      source: params.source ?? "llm",
      mastery_score: params.mastery_score ?? 0.5,
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to save learn content (${res.status}): ${detail}`);
  }

  return res.json();
}

/**
 * List all saved learning materials.
 */
export async function fetchLearnHistory(): Promise<LearnHistoryResponse> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/learn/history"));

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch learn history (${res.status}): ${detail}`);
  }

  return res.json();
}

/**
 * Get a specific learning material by filename.
 */
export async function fetchLearnContent(filename: string): Promise<LearnContentResponse> {
  const res = await apiFetch(apiUrl(`/api/v1/exam-sprint/learn/history/${encodeURIComponent(filename)}`));

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch learn content (${res.status}): ${detail}`);
  }

  return res.json();
}

/**
 * Delete a specific learning material.
 */
export async function deleteLearnContent(filename: string): Promise<void> {
  const res = await apiFetch(apiUrl(`/api/v1/exam-sprint/learn/history/${encodeURIComponent(filename)}`), {
    method: "DELETE",
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to delete learn content (${res.status}): ${detail}`);
  }
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

// ---------------------------------------------------------------------------
// Diagnosis report
// ---------------------------------------------------------------------------

export interface DiagnosisQuestion {
  question_id: string;
  question: string;
  correct_answer: string;
  user_answer: string;
  is_correct: boolean;
  error_type: string;
  knowledge_point: string;
}

export interface DiagnosisReport {
  completed_at: string;
  total_questions: number;
  correct: number;
  overall_score: number;
  questions: DiagnosisQuestion[];
  weak_points: string[];
  strong_points: string[];
}

/**
 * Get the diagnosis report from profile.
 */
export async function fetchDiagnosisReport(): Promise<DiagnosisReport> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/diagnosis/report"));

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch diagnosis report (${res.status}): ${detail}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Practice history — wrong questions for review
// ---------------------------------------------------------------------------

export interface PracticeHistoryItem {
  id: string;
  question_id: string;
  question: string;
  question_type: string;
  options: Record<string, string> | null;
  correct_answer: string;
  user_answer: string;
  error_type: string;
  knowledge_point: string;
  explanation: string;
  source: string;
  saved_at: string;
}

export interface PracticeHistoryResponse {
  items: PracticeHistoryItem[];
  count: number;
}

/**
 * List practice history (wrong questions), optionally filtered by knowledge point.
 */
export async function fetchPracticeHistory(
  knowledgePoint?: string,
): Promise<PracticeHistoryResponse> {
  const params = knowledgePoint ? `?knowledge_point=${encodeURIComponent(knowledgePoint)}` : "";
  const res = await apiFetch(apiUrl(`/api/v1/exam-sprint/practice/history${params}`));

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch practice history (${res.status}): ${detail}`);
  }

  return res.json();
}

/**
 * Get a specific practice history record.
 */
export async function fetchPracticeRecord(recordId: string): Promise<PracticeHistoryItem> {
  const res = await apiFetch(apiUrl(`/api/v1/exam-sprint/practice/history/${encodeURIComponent(recordId)}`));

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch practice record (${res.status}): ${detail}`);
  }

  return res.json();
}

/**
 * Delete a specific practice history record.
 */
export async function deletePracticeRecord(recordId: string): Promise<void> {
  const res = await apiFetch(apiUrl(`/api/v1/exam-sprint/practice/history/${encodeURIComponent(recordId)}`), {
    method: "DELETE",
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to delete practice record (${res.status}): ${detail}`);
  }
}
