"use client";

import { BookOpen, Dumbbell } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { SprintTask } from "./types";

interface SprintTaskListProps {
  tasks: SprintTask[];
  onAction: (task: SprintTask, action: "learn" | "practice") => void;
}

export function SprintTaskList({ tasks, onAction }: SprintTaskListProps) {
  const { t } = useTranslation();

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--secondary)]/30">
      <div className="flex items-center justify-between border-b border-[var(--border)]/60 px-4 py-2.5">
        <span className="text-sm font-medium text-[var(--foreground)]">
          {t("Today's Tasks")}
        </span>
        <span className="text-[11px] text-[var(--muted-foreground)]">
          {tasks.length} {t("tasks")}
        </span>
      </div>
      <div className="divide-y divide-[var(--border)]/40">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="flex items-center justify-between gap-3 px-4 py-3"
          >
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-[var(--foreground)]">
                {task.knowledge_point}
              </div>
              <div className="text-[11px] text-[var(--muted-foreground)]">
                ~{task.estimated_minutes} min
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => onAction(task, "learn")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:bg-[var(--muted)]"
              >
                <BookOpen size={13} />
                {t("Learn")}
              </button>
              <button
                type="button"
                onClick={() => onAction(task, "practice")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90"
              >
                <Dumbbell size={13} />
                {t("Practice")}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
