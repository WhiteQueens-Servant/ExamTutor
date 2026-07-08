"use client";

import { useState, useEffect } from "react";
import { X, FileText, Trash2, Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import MarkdownRenderer from "@/components/common/MarkdownRenderer";
import {
  fetchLearnHistory,
  fetchLearnContent,
  deleteLearnContent,
  type LearnHistoryItem,
} from "@/lib/exam-sprint-api";

interface LearnHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function LearnHistoryDrawer({ open, onClose }: LearnHistoryDrawerProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<LearnHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<LearnHistoryItem | null>(null);
  const [content, setContent] = useState("");
  const [contentLoading, setContentLoading] = useState(false);

  useEffect(() => {
    if (open) {
      loadHistory();
    }
  }, [open]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const result = await fetchLearnHistory();
      setItems(result.items);
    } catch (err) {
      console.error("Failed to load learn history:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewItem = async (item: LearnHistoryItem) => {
    setSelectedItem(item);
    setContentLoading(true);
    try {
      const result = await fetchLearnContent(item.filename);
      setContent(result.content);
    } catch (err) {
      console.error("Failed to load content:", err);
      setContent("");
    } finally {
      setContentLoading(false);
    }
  };

  const handleDelete = async (filename: string) => {
    try {
      await deleteLearnContent(filename);
      setItems(items.filter((item) => item.filename !== filename));
      if (selectedItem?.filename === filename) {
        setSelectedItem(null);
        setContent("");
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
            {t("Learn History")}
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
          <div className="w-1/3 border-r border-[var(--border)] overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
              </div>
            )}

            {!loading && items.length === 0 && (
              <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                {t("No saved materials yet")}
              </div>
            )}

            {!loading && items.map((item) => (
              <div
                key={item.filename}
                className={`flex items-start gap-2 border-b border-[var(--border)] px-3 py-2 cursor-pointer hover:bg-[var(--muted)] ${
                  selectedItem?.filename === item.filename ? "bg-[var(--muted)]" : ""
                }`}
                onClick={() => handleViewItem(item)}
              >
                <FileText size={14} className="mt-0.5 shrink-0 text-[var(--muted-foreground)]" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-[var(--foreground)]">
                    {item.knowledge_point}
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-[var(--muted-foreground)]">
                    <Clock size={10} />
                    {new Date(item.saved_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(item.filename);
                  }}
                  className="shrink-0 rounded p-1 text-[var(--muted-foreground)] hover:bg-rose-100 hover:text-rose-600"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>

          {/* Content preview */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {contentLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
              </div>
            )}

            {!contentLoading && !selectedItem && (
              <div className="py-12 text-center text-sm text-[var(--muted-foreground)]">
                {t("Select an item to view")}
              </div>
            )}

            {!contentLoading && selectedItem && content && (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <MarkdownRenderer content={content} enableMath enableCode />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
