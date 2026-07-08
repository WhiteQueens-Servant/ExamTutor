"use client";

import { useState, useEffect } from "react";
import { X, CheckCircle, XCircle, TrendingDown, TrendingUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  fetchDiagnosisReport,
  type DiagnosisReport,
  type DiagnosisQuestion,
} from "@/lib/exam-sprint-api";

interface DiagnosticReportDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function DiagnosticReportDrawer({ open, onClose }: DiagnosticReportDrawerProps) {
  const { t } = useTranslation();
  const [report, setReport] = useState<DiagnosisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<DiagnosisQuestion | null>(null);

  useEffect(() => {
    if (open) {
      loadReport();
    }
  }, [open]);

  const loadReport = async () => {
    setLoading(true);
    try {
      const result = await fetchDiagnosisReport();
      setReport(result);
    } catch (err) {
      console.error("Failed to load diagnosis report:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Drawer panel */}
      <div className="relative flex w-full max-w-2xl flex-col border-l border-[var(--border)] bg-[var(--background)] shadow-xl">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-[var(--border)] px-4 py-3">
          <div className="text-sm font-semibold text-[var(--foreground)]">
            {t("Diagnosis Report")}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Summary + Question list */}
          <div className="w-1/2 border-r border-[var(--border)] overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
              </div>
            )}

            {!loading && !report && (
              <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                {t("No diagnosis report available")}
              </div>
            )}

            {!loading && report && (
              <div className="p-4">
                {/* Summary stats */}
                <div className="mb-4 grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-[var(--border)] p-3">
                    <div className="text-2xl font-bold text-[var(--foreground)]">
                      {Math.round(report.overall_score * 100)}%
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)]">
                      {t("Overall Score")}
                    </div>
                  </div>
                  <div className="rounded-lg border border-[var(--border)] p-3">
                    <div className="text-2xl font-bold text-[var(--foreground)]">
                      {report.correct}/{report.total_questions}
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)]">
                      {t("Correct")}
                    </div>
                  </div>
                </div>

                {/* Weak/Strong points */}
                {report.weak_points.length > 0 && (
                  <div className="mb-3">
                    <div className="flex items-center gap-1 text-xs font-medium text-rose-600 mb-1">
                      <TrendingDown size={12} />
                      {t("Weak Points")}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {report.weak_points.map((wp) => (
                        <span key={wp} className="rounded bg-rose-100 px-2 py-0.5 text-xs text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
                          {wp}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {report.strong_points.length > 0 && (
                  <div className="mb-4">
                    <div className="flex items-center gap-1 text-xs font-medium text-emerald-600 mb-1">
                      <TrendingUp size={12} />
                      {t("Strong Points")}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {report.strong_points.map((sp) => (
                        <span key={sp} className="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                          {sp}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Question list */}
                <div className="text-xs font-medium text-[var(--muted-foreground)] mb-2">
                  {t("Questions")} ({report.questions.length})
                </div>
                <div className="space-y-1">
                  {report.questions.map((q, idx) => (
                    <div
                      key={q.question_id || idx}
                      className={`flex items-start gap-2 rounded-lg px-2 py-1.5 cursor-pointer hover:bg-[var(--muted)] ${
                        selectedQuestion === q ? "bg-[var(--muted)]" : ""
                      }`}
                      onClick={() => setSelectedQuestion(q)}
                    >
                      {q.is_correct ? (
                        <CheckCircle size={14} className="mt-0.5 shrink-0 text-emerald-500" />
                      ) : (
                        <XCircle size={14} className="mt-0.5 shrink-0 text-rose-500" />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm text-[var(--foreground)]">
                          {idx + 1}. {q.question.slice(0, 40)}...
                        </div>
                        <div className="text-[11px] text-[var(--muted-foreground)]">
                          {q.knowledge_point}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Detail view */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {!selectedQuestion && (
              <div className="py-12 text-center text-sm text-[var(--muted-foreground)]">
                {t("Select a question to view details")}
              </div>
            )}

            {selectedQuestion && (
              <div className="space-y-4">
                {/* Question */}
                <div>
                  <h4 className="text-sm font-medium text-[var(--foreground)] mb-2">
                    {t("Question")}
                  </h4>
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)] p-3 text-sm">
                    {selectedQuestion.question}
                  </div>
                </div>

                {/* Answers comparison */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <h4 className="text-sm font-medium text-rose-600 mb-1 flex items-center gap-1">
                      <XCircle size={14} />
                      {t("Your Answer")}
                    </h4>
                    <div className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-sm text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300">
                      {selectedQuestion.user_answer || t("No answer")}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-emerald-600 mb-1 flex items-center gap-1">
                      <CheckCircle size={14} />
                      {t("Correct Answer")}
                    </h4>
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-2 text-sm text-emerald-700 dark:border-emerald-800/30 dark:bg-emerald-950/20 dark:text-emerald-300">
                      {selectedQuestion.correct_answer}
                    </div>
                  </div>
                </div>

                {/* Error type */}
                {selectedQuestion.error_type && (
                  <div>
                    <h4 className="text-sm font-medium text-[var(--foreground)] mb-1">
                      {t("Error Type")}
                    </h4>
                    <div className="text-sm text-[var(--muted-foreground)]">
                      {selectedQuestion.error_type}
                    </div>
                  </div>
                )}

                {/* Knowledge point */}
                <div>
                  <h4 className="text-sm font-medium text-[var(--foreground)] mb-1">
                    {t("Knowledge Point")}
                  </h4>
                  <div className="rounded bg-[var(--muted)] px-2 py-1 text-sm inline-block">
                    {selectedQuestion.knowledge_point}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
