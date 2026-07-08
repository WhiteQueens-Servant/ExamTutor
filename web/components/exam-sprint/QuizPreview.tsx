"use client";

import { useState, useCallback } from "react";
import { CheckCircle, XCircle } from "lucide-react";
import MarkdownRenderer from "@/components/common/MarkdownRenderer";
import type { QuizQuestion } from "@/lib/quiz-types";
import type { QuizAnswerRecord } from "./QuizDrawer";

interface QuizPreviewProps {
  questions: QuizQuestion[];
  onComplete?: (answers: QuizAnswerRecord[]) => void;
}

/**
 * Lightweight quiz preview — displays questions without backend dependencies.
 * Used in QuizDrawer for V0. Will be replaced by full QuizViewer in Phase 4
 * when backend is connected.
 */
export function QuizPreview({ questions, onComplete }: QuizPreviewProps) {
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState<Record<number, boolean>>({});
  const [completed, setCompleted] = useState(false);

  const q = questions[idx];
  const total = questions.length;

  const handleComplete = useCallback(() => {
    if (completed || !onComplete) return;

    // Collect wrong answers
    const wrongAnswers: QuizAnswerRecord[] = [];
    questions.forEach((q, i) => {
      const userAnswer = answers[i] ?? "";
      const isCorrect = userAnswer === q.correct_answer;
      if (!isCorrect && userAnswer) {
        wrongAnswers.push({
          question_id: q.question_id,
          question: q.question,
          question_type: q.question_type,
          options: q.options,
          correct_answer: q.correct_answer,
          user_answer: userAnswer,
          is_correct: false,
          error_type: "wrong_answer",
          knowledge_point: q.concentration ?? "unknown",
          explanation: q.explanation,
        });
      }
    });

    setCompleted(true);
    onComplete(wrongAnswers);
  }, [answers, questions, onComplete, completed]);

  if (!q) {
    return (
      <div className="py-10 text-center text-sm text-[var(--muted-foreground)]">
        No questions available.
      </div>
    );
  }

  const isChoice = q.question_type === "choice" && q.options;
  const isConcept = q.question_type === "concept";
  const currentAnswer = answers[idx] ?? "";
  const isSubmitted = submitted[idx] ?? false;
  const isCorrect = isSubmitted && currentAnswer === q.correct_answer;

  const handleSubmit = () => {
    if (!currentAnswer) return;
    setSubmitted((prev) => ({ ...prev, [idx]: true }));
  };

  const handleNext = () => {
    if (idx < total - 1) {
      setIdx((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (idx > 0) {
      setIdx((prev) => prev - 1);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Progress */}
      <div className="flex items-center justify-between text-xs text-[var(--muted-foreground)]">
        <span>
          {idx + 1} / {total}
        </span>
        <span>{q.difficulty || "—"}</span>
      </div>

      {/* Question */}
      <div className="text-sm font-medium text-[var(--foreground)]">
        <MarkdownRenderer content={q.question} enableMath enableCode={false} />
      </div>

      {/* Options */}
      {isChoice && q.options && (
        <div className="flex flex-col gap-2">
          {Object.entries(q.options).map(([key, label]) => {
            const selected = currentAnswer === key;
            return (
              <button
                key={key}
                type="button"
                disabled={isSubmitted}
                onClick={() => setAnswers((prev) => ({ ...prev, [idx]: key }))}
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  selected
                    ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)]"
                    : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
                } ${isSubmitted && key === q.correct_answer ? "border-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/20" : ""} ${isSubmitted && selected && !isCorrect ? "border-rose-300 bg-rose-50/50 dark:bg-rose-950/20" : ""}`}
              >
                <span className="font-mono text-xs">{key}</span>
                <span><MarkdownRenderer content={label} enableMath enableCode={false} /></span>
                {isSubmitted && key === q.correct_answer && (
                  <CheckCircle size={14} className="ml-auto text-emerald-500" />
                )}
                {isSubmitted && selected && !isCorrect && (
                  <XCircle size={14} className="ml-auto text-rose-400" />
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Concept (T/F) */}
      {isConcept && (
        <div className="flex gap-2">
          {["true", "false"].map((val) => {
            const selected = currentAnswer === val;
            return (
              <button
                key={val}
                type="button"
                disabled={isSubmitted}
                onClick={() => setAnswers((prev) => ({ ...prev, [idx]: val }))}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm transition-colors ${
                  selected
                    ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)]"
                    : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
                }`}
              >
                {val === "true" ? "True" : "False"}
              </button>
            );
          })}
        </div>
      )}

      {/* Fill in blank */}
      {!isChoice && !isConcept && (
        <input
          type="text"
          disabled={isSubmitted}
          value={currentAnswer}
          onChange={(e) =>
            setAnswers((prev) => ({ ...prev, [idx]: e.target.value }))
          }
          placeholder="Type your answer…"
          className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]/50 focus:border-[var(--primary)] focus:outline-none"
        />
      )}

      {/* Result + explanation */}
      {isSubmitted && (
        <div
          className={`rounded-lg border px-3 py-2 text-sm ${
            isCorrect
              ? "border-emerald-200 bg-emerald-50/50 text-emerald-700 dark:border-emerald-800/30 dark:bg-emerald-950/20 dark:text-emerald-300"
              : "border-rose-200 bg-rose-50/50 text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300"
          }`}
        >
          {isCorrect ? "Correct!" : `Incorrect. Answer: ${q.correct_answer}`}
          {q.explanation && (
            <div className="mt-1 text-xs opacity-80">
              <MarkdownRenderer content={q.explanation} enableMath enableCode={false} />
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          onClick={handlePrev}
          disabled={idx === 0}
          className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted-foreground)] hover:bg-[var(--muted)] disabled:opacity-40"
        >
          Previous
        </button>
        <div className="flex gap-2">
          {!isSubmitted ? (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!currentAnswer}
              className="rounded-lg bg-[var(--primary)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-40"
            >
              Submit
            </button>
          ) : idx < total - 1 ? (
            <button
              type="button"
              onClick={handleNext}
              className="rounded-lg bg-[var(--primary)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
            >
              Next
            </button>
          ) : !completed ? (
            <button
              type="button"
              onClick={handleComplete}
              className="rounded-lg bg-[var(--primary)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
            >
              Complete
            </button>
          ) : (
            <span className="text-xs text-[var(--muted-foreground)]">
              All questions completed
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
