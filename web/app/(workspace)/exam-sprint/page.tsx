"use client";

import { Target } from "lucide-react";
import { useTranslation } from "react-i18next";

export default function ExamSprintPage() {
  const { t } = useTranslation();

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
              Exam preparation with time-pressure planning.
            </div>
          </div>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-[var(--muted-foreground)]">
          <Target size={40} strokeWidth={1.2} />
          <p className="text-sm">Exam Sprint — Coming Soon</p>
        </div>
      </main>
    </div>
  );
}
