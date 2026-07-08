"use client";

import { useState, useEffect } from "react";
import { X, AlertCircle, Trash2, Clock, CheckCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  fetchPracticeHistory,
  deletePracticeRecord,
  type PracticeHistoryItem,
} from "@/lib/exam-sprint-api";

interface PracticeHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function PracticeHistoryDrawer({ open, onClose }: PracticeHistoryDrawerProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<PracticeHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<PracticeHistoryItem | null>(null);

  useEffect(() => {
    if (open) {
      loadHistory();
    }
  }, [open]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const result = await fetchPracticeHistory();
      setItems(result.items);
    } catch (err) {
      console.error("Failed to load practice history:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePracticeRecord(id);
      setItems(items.filter((item) => item.id !== id));
      if (selectedItem?.id === id) {
        setSelectedItem(null);
      }
    } catch (err) {
      console.error("Failed to delete:", err);
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
            {t("Practice History")}
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
          {/* History list */}
          <div className="w-1/2 border-r border-[var(--border)] overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
              </div>
            )}

            {!loading && items.length === 0 && (
              <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                {t("No wrong questions yet")}
              </div>
            )}

            {!loading && items.map((item) => (
              <div
                key={item.id}
                className={`flex items-start gap-2 border-b border-[var(--border)] px-3 py-2 cursor-pointer hover:bg-[var(--muted)] ${
                  selectedItem?.id === item.id ? "bg-[var(--muted)]" : ""
                }`}
                onClick={() => setSelectedItem(item)}
              >
                <AlertCircle size={14} className="mt-0.5 shrink-0 text-rose-500" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-[var(--foreground)]">
                    {item.question.slice(0, 50)}...
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
                    <span className="rounded bg-rose-100 px-1.5 py-0.5 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
                      {item.knowledge_point}
                    </span>
                    <Clock size={10} />
                    {new Date(item.saved_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(item.id);
                  }}
                  className="shrink-0 rounded p-1 text-[var(--muted-foreground)] hover:bg-rose-100 hover:text-rose-600"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>

          {/* Detail view */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {!selectedItem && (
              <div className="py-12 text-center text-sm text-[var(--muted-foreground)]">
                {t("Select a question to view details")}
              </div>
            )}

            {selectedItem && (
              <div className="space-y-4">
                {/* Question */}
                <div>
                  <h4 className="text-sm font-medium text-[var(--foreground)] mb-2">
                    {t("Question")}
                  </h4>
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)] p-3 text-sm">
                    {selectedItem.question}
                  </div>
                </div>

                {/* Options (if any) */}
                {selectedItem.options && Object.keys(selectedItem.options).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-[var(--foreground)] mb-2">
                      {t("Options")}
                    </h4>
                    <div className="space-y-1">
                      {Object.entries(selectedItem.options).map(([key, value]) => (
                        <div key={key} className="flex items-center gap-2 text-sm">
                          <span className="font-medium">{key}.</span>
                          <span>{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Answers comparison */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <h4 className="text-sm font-medium text-rose-600 mb-1 flex items-center gap-1">
                      <X size={14} />
                      {t("Your Answer")}
                    </h4>
                    <div className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-sm text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300">
                      {selectedItem.user_answer || t("No answer")}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-emerald-600 mb-1 flex items-center gap-1">
                      <CheckCircle size={14} />
                      {t("Correct Answer")}
                    </h4>
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-2 text-sm text-emerald-700 dark:border-emerald-800/30 dark:bg-emerald-950/20 dark:text-emerald-300">
                      {selectedItem.correct_answer}
                    </div>
                  </div>
                </div>

                {/* Error type */}
                {selectedItem.error_type && (
                  <div>
                    <h4 className="text-sm font-medium text-[var(--foreground)] mb-1">
                      {t("Error Type")}
                    </h4>
                    <div className="text-sm text-[var(--muted-foreground)]">
                      {selectedItem.error_type}
                    </div>
                  </div>
                )}

                {/* Explanation */}
                {selectedItem.explanation && (
                  <div>
                    <h4 className="text-sm font-medium text-[var(--foreground)] mb-1">
                      {t("Explanation")}
                    </h4>
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)] p-3 text-sm">
                      {selectedItem.explanation}
                    </div>
                  </div>
                )}

                {/* Source */}
                <div className="text-xs text-[var(--muted-foreground)]">
                  {t("Source")}: {selectedItem.source === "diagnosis" ? t("Diagnosis") : t("Practice")}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
