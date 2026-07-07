"use client";

import { useState } from "react";
import { Target } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ExamMasteryTable } from "@/components/exam-sprint/ExamMasteryTable";
import { QuizDrawer } from "@/components/exam-sprint/QuizDrawer";
import { SprintTaskList } from "@/components/exam-sprint/SprintTaskList";
import { StatCards } from "@/components/exam-sprint/StatCards";
import { TopWeakBanner } from "@/components/exam-sprint/TopWeakBanner";
import {
  MOCK_META,
  MOCK_MASTERY,
  MOCK_TASKS,
  MOCK_QUIZ_QUESTIONS,
} from "@/components/exam-sprint/types";
import type { SprintTask } from "@/components/exam-sprint/types";

export default function ExamSprintPage() {
  const { t } = useTranslation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTitle, setDrawerTitle] = useState("");

  const handleTaskAction = (task: SprintTask, action: "learn" | "practice") => {
    if (action === "practice") {
      setDrawerTitle(`${task.knowledge_point} — ${t("Practice")}`);
      setDrawerOpen(true);
    }
    // "learn" action will be wired in Phase 4 (RAG + Markdown)
  };

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
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-5">
        <div className="mx-auto flex max-w-4xl flex-col gap-5">
          {/* Time pressure banner */}
          <TopWeakBanner data={MOCK_MASTERY} />

          {/* Stat cards */}
          <StatCards meta={MOCK_META} />

          {/* Task list */}
          <SprintTaskList tasks={MOCK_TASKS} onAction={handleTaskAction} />

          {/* Mastery table */}
          <ExamMasteryTable data={MOCK_MASTERY} />
        </div>
      </main>

      {/* Quiz drawer */}
      <QuizDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        questions={MOCK_QUIZ_QUESTIONS}
        title={drawerTitle}
      />
    </div>
  );
}
