"use client";

import { Loader2, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { QuizQuestion } from "@/lib/quiz-types";
import { QuizPreview } from "./QuizPreview";

export interface QuizAnswerRecord {
  question_id: string;
  question: string;
  question_type: string;
  options?: Record<string, string> | null;
  correct_answer: string;
  user_answer: string;
  is_correct: boolean;
  error_type: string;
  knowledge_point: string;
  explanation?: string;
}

interface QuizDrawerProps {
  open: boolean;
  onClose: () => void;
  questions: QuizQuestion[];
  title?: string;
  loading?: boolean;
  error?: string | null;
  onComplete?: (answers: QuizAnswerRecord[]) => void;
}

export function QuizDrawer({
  open,
  onClose,
  questions,
  title,
  loading = false,
  error = null,
  onComplete,
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
              {loading
                ? t("Generating questions...")
                : error
                  ? t("Error")
                  : `${questions.length} ${t("questions")}`}
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
          {loading && (
            <div className="flex flex-col items-center justify-center gap-3 py-16">
              <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
              <div className="text-sm text-[var(--muted-foreground)]">
                {t("Generating questions...")}
              </div>
            </div>
          )}

          {error && !loading && (
            <div className="rounded-lg border border-rose-200 bg-rose-50/50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300">
              {error}
            </div>
          )}

          {!loading && !error && questions.length > 0 && (
            <QuizPreview questions={questions} onComplete={onComplete} />
          )}

          {!loading && !error && questions.length === 0 && (
            <div className="py-10 text-center text-sm text-[var(--muted-foreground)]">
              {t("No questions available.")}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
