"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { MasteryEntry } from "./types";

export function TopWeakBanner({ data }: { data: MasteryEntry[] }) {
  const { t } = useTranslation();

  // Find the weakest topic (lowest score)
  const weakest = [...data].sort((a, b) => a.score - b.score)[0];
  if (!weakest || weakest.score >= 0.6) return null;

  return (
    <div className="flex items-center gap-3 rounded-xl border border-rose-200/50 bg-rose-50/40 px-4 py-3 dark:border-rose-800/30 dark:bg-rose-950/20">
      <AlertTriangle
        size={16}
        className="shrink-0 text-rose-500 dark:text-rose-400"
      />
      <div className="min-w-0 flex-1 text-sm">
        <span className="font-medium text-rose-700 dark:text-rose-300">
          {weakest.knowledge_point}
        </span>
        <span className="mx-1.5 text-rose-400/60">—</span>
        <span className="text-rose-600/80 dark:text-rose-400/80">
          {t("mastery only")} {Math.round(weakest.score * 100)}%
          {". "}
          {t("Prioritize this topic before the exam.")}
        </span>
      </div>
    </div>
  );
}
