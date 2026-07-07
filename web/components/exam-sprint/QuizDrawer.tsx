"use client";

import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { QuizQuestion } from "@/lib/quiz-types";
import { QuizPreview } from "./QuizPreview";

interface QuizDrawerProps {
  open: boolean;
  onClose: () => void;
  questions: QuizQuestion[];
  title?: string;
}

export function QuizDrawer({
  open,
  onClose,
  questions,
  title,
}: QuizDrawerProps) {
  const { t } = useTranslation();

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-[var(--background)] shadow-xl transition-transform">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-[var(--border)] px-4 py-3">
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold text-[var(--foreground)]">
              {title || t("Practice")}
            </div>
            <div className="text-[11px] text-[var(--muted-foreground)]">
              {questions.length} {t("questions")}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-3 rounded-md p-1.5 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
          >
            <X size={16} />
          </button>
        </div>

        {/* Quiz body */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <QuizPreview questions={questions} />
        </div>
      </div>
    </>
  );
}
