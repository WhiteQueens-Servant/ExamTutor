"use client";

import { useState } from "react";
import { Calendar, BookOpen, Clock } from "lucide-react";
import { useTranslation } from "react-i18next";

interface SetupModalProps {
  open: boolean;
  onSubmit: (data: {
    exam_name: string;
    exam_date: string;
    daily_budget_minutes: number;
  }) => void;
  loading: boolean;
  error: string | null;
}

export function SetupModal({ open, onSubmit, loading, error }: SetupModalProps) {
  const { t } = useTranslation();
  const [examName, setExamName] = useState("");
  const [examDate, setExamDate] = useState("");
  const [budget, setBudget] = useState(120);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!examName.trim() || !examDate) return;
    onSubmit({
      exam_name: examName.trim(),
      exam_date: examDate,
      daily_budget_minutes: budget,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" />

      {/* Modal */}
      <div className="relative w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--background)] p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--primary)]/10">
            <BookOpen size={24} className="text-[var(--primary)]" />
          </div>
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            {t("Welcome to Exam Sprint")}
          </h2>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            {t("Set up your exam to start your study plan")}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Exam name */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-[var(--foreground)]">
              <BookOpen size={14} />
              {t("Exam Name")}
            </label>
            <input
              type="text"
              value={examName}
              onChange={(e) => setExamName(e.target.value)}
              placeholder={t("e.g. Signal & Systems Final Exam")}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]/40"
              required
            />
          </div>

          {/* Exam date */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-[var(--foreground)]">
              <Calendar size={14} />
              {t("Exam Date")}
            </label>
            <input
              type="date"
              value={examDate}
              onChange={(e) => setExamDate(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]/40"
              required
            />
          </div>

          {/* Daily budget */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-[var(--foreground)]">
              <Clock size={14} />
              {t("Daily Study Budget (minutes)")}
            </label>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              min={10}
              max={480}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]/40"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !examName.trim() || !examDate}
            className="w-full rounded-lg bg-[var(--primary)] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? t("Setting up...") : t("Start Sprint")}
          </button>
        </form>
      </div>
    </div>
  );
}
