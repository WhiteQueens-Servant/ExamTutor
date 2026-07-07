/**
 * Exam Sprint type definitions and mock data.
 *
 * V0: All data is mocked. Real data will come from backend in Phase 4.
 */

export interface MasteryEntry {
  knowledge_point: string;
  score: number; // 0.0 - 1.0
  surface: "notebook" | "quiz" | "chat" | "kb" | "book";
}

export interface SprintTask {
  id: string;
  knowledge_point: string;
  action: "learn" | "practice";
  priority: number;
  estimated_minutes: number;
}

export interface SprintMeta {
  exam_name: string;
  exam_date: string; // ISO date
  days_remaining: number;
  phase: "phase_planning" | "sprint_week" | "score_protection";
  streak: number;
  total_tasks_today: number;
  completed_tasks_today: number;
}

// ── Mock data ──────────────────────────────────────────────────────────

export const MOCK_MASTERY: MasteryEntry[] = [
  { knowledge_point: "傅里叶变换", score: 0.35, surface: "notebook" },
  { knowledge_point: "拉普拉斯变换", score: 0.72, surface: "quiz" },
  { knowledge_point: "卷积定理", score: 0.18, surface: "chat" },
  { knowledge_point: "Z变换", score: 0.55, surface: "notebook" },
  { knowledge_point: "采样定理", score: 0.88, surface: "quiz" },
  { knowledge_point: "频率响应", score: 0.42, surface: "kb" },
  { knowledge_point: "离散傅里叶变换", score: 0.61, surface: "book" },
  { knowledge_point: "信号采样", score: 0.29, surface: "notebook" },
];

export const MOCK_TASKS: SprintTask[] = [
  { id: "t1", knowledge_point: "卷积定理", action: "learn", priority: 1, estimated_minutes: 15 },
  { id: "t2", knowledge_point: "傅里叶变换", action: "practice", priority: 2, estimated_minutes: 10 },
  { id: "t3", knowledge_point: "信号采样", action: "learn", priority: 3, estimated_minutes: 12 },
  { id: "t4", knowledge_point: "频率响应", action: "practice", priority: 4, estimated_minutes: 8 },
];

export const MOCK_META: SprintMeta = {
  exam_name: "信号与系统 期末考试",
  exam_date: "2026-07-25",
  days_remaining: 18,
  phase: "sprint_week",
  streak: 5,
  total_tasks_today: 4,
  completed_tasks_today: 1,
};
