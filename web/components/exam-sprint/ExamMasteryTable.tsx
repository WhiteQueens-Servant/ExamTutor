"use client";

import { useTranslation } from "react-i18next";
import type { MasteryEntry } from "./types";

function MasteryBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  let color = "bg-rose-400 dark:bg-rose-500";
  if (score >= 0.7) color = "bg-emerald-400 dark:bg-emerald-500";
  else if (score >= 0.4) color = "bg-amber-400 dark:bg-amber-500";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-[var(--border)]/40">
        <div
          className={`h-full rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-9 text-right text-xs tabular-nums text-[var(--muted-foreground)]">
        {pct}%
      </span>
    </div>
  );
}

const SURFACE_LABELS: Record<string, string> = {
  notebook: "Notebook",
  quiz: "Quiz",
  chat: "Chat",
  kb: "KB",
  book: "Book",
  diagnosis: "Diagnosis",
};

export function ExamMasteryTable({ data }: { data: MasteryEntry[] }) {
  const { t } = useTranslation();

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--secondary)]/30">
      <div className="flex items-center justify-between border-b border-[var(--border)]/60 px-4 py-2.5">
        <span className="text-sm font-medium text-[var(--foreground)]">
          {t("Mastery Overview")}
        </span>
        <span className="text-[11px] text-[var(--muted-foreground)]">
          {data.length} {t("topics")}
        </span>
      </div>
      <div className="divide-y divide-[var(--border)]/40">
        {data.map((entry) => (
          <div
            key={entry.knowledge_point}
            className="flex items-center justify-between gap-4 px-4 py-2.5"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm text-[var(--foreground)]">
                {entry.knowledge_point}
              </div>
              <div className="text-[11px] text-[var(--muted-foreground)]">
                {SURFACE_LABELS[entry.surface] || entry.surface}
              </div>
            </div>
            <MasteryBar score={entry.score} />
          </div>
        ))}
      </div>
    </div>
  );
}
