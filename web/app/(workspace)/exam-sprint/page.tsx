"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, Target } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ExamMasteryTable } from "@/components/exam-sprint/ExamMasteryTable";
import { QuizDrawer } from "@/components/exam-sprint/QuizDrawer";
import { SprintTaskList } from "@/components/exam-sprint/SprintTaskList";
import { StatCards } from "@/components/exam-sprint/StatCards";
import { TopWeakBanner } from "@/components/exam-sprint/TopWeakBanner";
import {
  MOCK_META,
  MOCK_TASKS,
} from "@/components/exam-sprint/types";
import type { MasteryEntry, SprintTask } from "@/components/exam-sprint/types";
import type { QuizQuestion } from "@/lib/quiz-types";
import { generateExamQuestions } from "@/lib/exam-sprint-api";
import { fetchMastery } from "@/lib/exam-sprint-mastery-api";
import { useKnowledgeBases } from "@/hooks/useKnowledgeBases";

export default function ExamSprintPage() {
  const { t } = useTranslation();
  const { kbs, loading: kbLoading } = useKnowledgeBases();
  const [selectedKb, setSelectedKb] = useState("");
  const [mastery, setMastery] = useState<MasteryEntry[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTitle, setDrawerTitle] = useState("");
  const [drawerQuestions, setDrawerQuestions] = useState<QuizQuestion[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  // Fetch mastery on mount
  useEffect(() => {
    fetchMastery()
      .then(setMastery)
      .catch((err) => {
        console.error("Failed to load mastery:", err);
        // Fall back to empty list — dashboard still renders
      });
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
      // "learn" action will be wired in Phase 4 (RAG + Markdown)
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
              {MOCK_META.exam_name}
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
          <StatCards meta={MOCK_META} />

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
    </div>
  );
}
