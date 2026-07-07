/**
 * Exam Sprint Mastery API client.
 */

import { apiFetch, apiUrl } from "./api";

export interface MasteryEntry {
  knowledge_point: string;
  score: number; // 0.0 - 1.0
  surface: "notebook" | "quiz" | "chat" | "kb" | "book";
}

/**
 * Fetch all mastery entries for the Exam Sprint dashboard.
 */
export async function fetchMastery(): Promise<MasteryEntry[]> {
  const res = await apiFetch(apiUrl("/api/v1/exam-sprint/mastery"));
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to fetch mastery (${res.status}): ${detail}`);
  }
  return await res.json();
}

/**
 * Update a single mastery entry after quiz completion.
 * Uses exponential moving average to blend new score with existing.
 */
export async function updateMastery(params: {
  knowledge_point: string;
  score: number;
  surface?: string;
}): Promise<MasteryEntry[]> {
  const res = await apiFetch(
    apiUrl("/api/v1/exam-sprint/mastery/update"),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        knowledge_point: params.knowledge_point,
        score: params.score,
        surface: params.surface ?? "quiz",
      }),
    },
  );
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Failed to update mastery (${res.status}): ${detail}`);
  }
  return await res.json();
}
