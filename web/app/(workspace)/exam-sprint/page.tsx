"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Database, Target } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ExamMasteryTable } from "@/components/exam-sprint/ExamMasteryTable";
import { LearnDrawer } from "@/components/exam-sprint/LearnDrawer";
import { QuizDrawer } from "@/components/exam-sprint/QuizDrawer";
import { SetupModal } from "@/components/exam-sprint/SetupModal";
import { SprintTaskList } from "@/components/exam-sprint/SprintTaskList";
import { StatCards } from "@/components/exam-sprint/StatCards";
import { TopWeakBanner } from "@/components/exam-sprint/TopWeakBanner";
import {
  MOCK_TASKS,
} from "@/components/exam-sprint/types";
import type { MasteryEntry, SprintTask } from "@/components/exam-sprint/types";
import type { QuizQuestion } from "@/lib/quiz-types";
import {
  fetchExamState,
  saveExamState,
  generateExamQuestions,
  generateLearnContent,
  type ExamState,
  type DiagnosisSubmitResult,
} from "@/lib/exam-sprint-api";
import { fetchMastery } from "@/lib/exam-sprint-mastery-api";
import { useKnowledgeBases } from "@/hooks/useKnowledgeBases";

export default function ExamSprintPage() {
  const { t } = useTranslation();
  const { kbs, loading: kbLoading } = useKnowledgeBases();
  const [selectedKb, setSelectedKb] = useState("");
  const [mastery, setMastery] = useState<MasteryEntry[]>([]);
  const [examState, setExamState] = useState<ExamState | null>(null);
  const [setupOpen, setSetupOpen] = useState(false);
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTitle, setDrawerTitle] = useState("");
  const [drawerQuestions, setDrawerQuestions] = useState<QuizQuestion[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  // Learn drawer state
  const [learnOpen, setLearnOpen] = useState(false);
  const [learnTitle, setLearnTitle] = useState("");
  const [learnContent, setLearnContent] = useState("");
  const [learnSource, setLearnSource] = useState<"rag" | "llm" | "">("");
  const [learnLoading, setLearnLoading] = useState(false);
  const [learnError, setLearnError] = useState<string | null>(null);

  // Fetch exam state + mastery on mount
  useEffect(() => {
    fetchExamState()
      .then((state) => {
        setExamState(state);
        // Cold start: onboarding not completed or no exam info
        if (!state.onboarding_completed || !state.exam_name || !state.exam_date) {
          setSetupOpen(true);
        }
      })
      .catch((err) => {
        console.error("Failed to load exam state:", err);
        setSetupOpen(true); // Show setup on error
      });

    fetchMastery()
      .then(setMastery)
      .catch((err) => {
        console.error("Failed to load mastery:", err);
      });
  }, []);

  // Compute meta from exam state (fallback to MOCK_META)
  const meta = useMemo(() => {
    if (!examState || !examState.exam_name) {
      return {
        exam_name: "Loading...",
        exam_date: "",
        days_remaining: 0,
        phase: "phase_planning" as const,
        streak: 0,
        total_tasks_today: 0,
        completed_tasks_today: 0,
      };
    }
    const examDate = new Date(examState.exam_date);
    const now = new Date();
    const daysRemaining = Math.max(0, Math.ceil((examDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));
    let phase: "phase_planning" | "sprint_week" | "score_protection" = "phase_planning";
    if (daysRemaining <= 3) phase = "score_protection";
    else if (daysRemaining <= 13) phase = "sprint_week";
    return {
      exam_name: examState.exam_name,
      exam_date: examState.exam_date,
      days_remaining: daysRemaining,
      phase,
      streak: examState.streak,
      total_tasks_today: examState.total_tasks_today,
      completed_tasks_today: examState.completed_tasks_today,
    };
  }, [examState]);

  // Setup handler
  const handleSetup = useCallback(async (data: {
    exam_name: string;
    exam_date: string;
    daily_budget_minutes: number;
    kb_name: string;
    diagnosis: DiagnosisSubmitResult | null;
  }) => {
    setSetupLoading(true);
    setSetupError(null);
    try {
      const state = await saveExamState({
        exam_name: data.exam_name,
        exam_date: data.exam_date,
        daily_budget_minutes: data.daily_budget_minutes,
        onboarding_completed: true,
        diagnosis_completed: data.diagnosis !== null,
        kb_name: data.kb_name,
      });
      setExamState(state);
      // Update mastery from diagnosis results
      if (data.diagnosis && data.diagnosis.knowledge_points) {
        setMastery(
          data.diagnosis.knowledge_points.map((kp) => ({
            knowledge_point: kp.name,
            score: kp.score,
            surface: "diagnosis",
          })),
        );
      }
      setSetupOpen(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setSetupError(msg);
    } finally {
      setSetupLoading(false);
    }
  }, []);

  const handleTaskAction = useCallback(
    async (task: SprintTask, action: "learn" | "practice") => {
      if (action === "practice") {
        setDrawerTitle(`${task.knowledge_point} — ${t("Practice")}`);
        setDrawerQuestions([]);
        setDrawerError(null);
        setDrawerLoading(true);
        setDrawerOpen(true);

        try {
          const questions = await generateExamQuestions({
            topic: task.knowledge_point,
            num_questions: 3,
            language: "zh",
            kb_name: selectedKb,
          });
          setDrawerQuestions(questions);
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          setDrawerError(msg);
        } finally {
          setDrawerLoading(false);
        }
      }

      if (action === "learn") {
        setLearnTitle(`${task.knowledge_point} — ${t("Learn")}`);
        setLearnContent("");
        setLearnSource("");
        setLearnError(null);
        setLearnLoading(true);
        setLearnOpen(true);

        try {
          const result = await generateLearnContent({
            knowledge_point: task.knowledge_point,
            kb_name: selectedKb,
            language: "zh",
          });
          setLearnContent(result.content);
          setLearnSource(result.source);
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          setLearnError(msg);
        } finally {
          setLearnLoading(false);
        }
      }
    },
    [t, selectedKb],
  );

  return (
    <div className="flex h-full min-h-full flex-col overflow-hidden bg-[var(--background)]">
      <header className="flex shrink-0 items-center justify-between border-b border-[var(--border)] px-6 py-3">
        <div className="flex items-center gap-3">
          <Target size={18} className="text-[var(--muted-foreground)]" />
          <div>
            <div className="text-sm font-semibold text-[var(--foreground)]">
              {t("Exam Sprint")}
            </div>
            <div className="text-xs text-[var(--muted-foreground)]">
              {meta.exam_name}
            </div>
          </div>
        </div>

        {/* Knowledge Base selector */}
        <div className="flex items-center gap-2">
          <Database size={14} className="text-[var(--muted-foreground)]" />
          <select
            value={selectedKb}
            onChange={(e) => setSelectedKb(e.target.value)}
            disabled={kbLoading}
            className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-[13px] text-[var(--foreground)] outline-none focus:border-[var(--primary)]/40"
          >
            <option value="">{t("No knowledge base (LLM only)")}</option>
            {kbs.map((kb) => (
              <option key={kb.name} value={kb.name}>
                {kb.name}
                {kb.is_default ? ` (${t("default")})` : ""}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-5">
        <div className="mx-auto flex max-w-4xl flex-col gap-5">
          {/* Time pressure banner */}
          <TopWeakBanner data={mastery} />

          {/* Stat cards */}
          <StatCards meta={meta} />

          {/* Task list */}
          <SprintTaskList tasks={MOCK_TASKS} onAction={handleTaskAction} />

          {/* Mastery table */}
          <ExamMasteryTable data={mastery} />
        </div>
      </main>

      {/* Quiz drawer */}
      <QuizDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        questions={drawerQuestions}
        title={drawerTitle}
        loading={drawerLoading}
        error={drawerError}
      />

      {/* Learn drawer */}
      <LearnDrawer
        open={learnOpen}
        onClose={() => setLearnOpen(false)}
        title={learnTitle}
        content={learnContent}
        source={learnSource}
        loading={learnLoading}
        error={learnError}
      />

      {/* Setup modal (cold start) */}
      <SetupModal
        open={setupOpen}
        onComplete={handleSetup}
        loading={setupLoading}
        error={setupError}
      />
    </div>
  );
}
