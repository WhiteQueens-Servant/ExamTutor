"use client";

import { X, Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import MarkdownRenderer from "@/components/common/MarkdownRenderer";

interface LearnDrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  content: string;
  source: "rag" | "llm" | "";
  loading: boolean;
  error: string | null;
  saved?: boolean;
}

export function LearnDrawer({
  open,
  onClose,
  title,
  content,
  source,
  loading,
  error,
  saved = false,
}: LearnDrawerProps) {
  const { t } = useTranslation();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Drawer panel */}
      <div className="relative flex w-full max-w-xl flex-col border-l border-[var(--border)] bg-[var(--background)] shadow-xl">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-[var(--border)] px-4 py-3">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-[var(--foreground)]">
              {title}
            </div>
            {source && (
              <div className="text-[11px] text-[var(--muted-foreground)]">
                {source === "rag" ? t("From Knowledge Base") : t("AI Generated")}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-2 rounded-lg p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
              <span className="ml-2 text-sm text-[var(--muted-foreground)]">
                {t("Generating learning material...")}
              </span>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300">
              {error}
            </div>
          )}

          {!loading && !error && content && (
            <>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <MarkdownRenderer content={content} enableMath enableCode />
              </div>
              {saved && (
                <div className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-800/30 dark:bg-emerald-950/20 dark:text-emerald-300">
                  <Check size={14} />
                  {t("Content saved to history")}
                </div>
              )}
            </>
          )}

          {!loading && !error && !content && (
            <div className="py-12 text-center text-sm text-[var(--muted-foreground)]">
              {t("No content available")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
