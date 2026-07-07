"use client";

import { useCallback, useRef, useState } from "react";
import {
  Calendar,
  BookOpen,
  Clock,
  Upload,
  FileText,
  ChevronRight,
  ChevronLeft,
  Check,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { QuizQuestion } from "@/lib/quiz-types";
import {
  generateDiagnosis,
  submitDiagnosis,
  type DiagnosisSubmitResult,
} from "@/lib/exam-sprint-api";
import {
  createKnowledgeBase,
  uploadKnowledgeBaseFiles,
} from "@/lib/knowledge-api";

interface SetupModalProps {
  open: boolean;
  onComplete: (data: {
    exam_name: string;
    exam_date: string;
    daily_budget_minutes: number;
    kb_name: string;
    diagnosis: DiagnosisSubmitResult | null;
  }) => void;
  loading: boolean;
  error: string | null;
}

type WizardStep = "exam_info" | "kb_upload" | "diagnosis" | "complete";

const STEPS: { key: WizardStep; label: string }[] = [
  { key: "exam_info", label: "Exam Info" },
  { key: "kb_upload", label: "Knowledge Base" },
  { key: "diagnosis", label: "Diagnosis" },
  { key: "complete", label: "Done" },
];

export function SetupModal({ open, onComplete, loading, error }: SetupModalProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<WizardStep>("exam_info");
  const [examName, setExamName] = useState("");
  const [examDate, setExamDate] = useState("");
  const [budget, setBudget] = useState(120);

  // KB state
  const [kbName, setKbName] = useState("");
  const [kbFiles, setKbFiles] = useState<File[]>([]);
  const [kbCreating, setKbCreating] = useState(false);
  const [kbError, setKbError] = useState<string | null>(null);
  const [kbCreated, setKbCreated] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Diagnosis state
  const [diagnosisQuestions, setDiagnosisQuestions] = useState<QuizQuestion[]>([]);
  const [diagnosisAnswers, setDiagnosisAnswers] = useState<Record<string, string>>({});
  const [diagnosisLoading, setDiagnosisLoading] = useState(false);
  const [diagnosisError, setDiagnosisError] = useState<string | null>(null);
  const [diagnosisSubmitting, setDiagnosisSubmitting] = useState(false);
  const [diagnosisResult, setDiagnosisResult] = useState<DiagnosisSubmitResult | null>(null);

  if (!open) return null;

  const currentStepIdx = STEPS.findIndex((s) => s.key === step);

  // ── Step 1: Exam Info ──
  const handleExamInfoNext = () => {
    if (!examName.trim() || !examDate) return;
    setKbName(examName.trim()); // Default KB name = exam name
    setStep("kb_upload");
  };

  // ── Step 2: KB Upload ──
  const handleCreateKB = async () => {
    if (!kbName.trim()) return;
    setKbCreating(true);
    setKbError(null);
    try {
      if (kbFiles.length > 0) {
        await createKnowledgeBase({
          name: kbName.trim(),
          provider: "llamaindex",
          files: kbFiles,
        });
      }
      setKbCreated(true);
    } catch (err) {
      setKbError(err instanceof Error ? err.message : String(err));
    } finally {
      setKbCreating(false);
    }
  };

  const handleKBNext = async () => {
    if (kbFiles.length === 0 || kbCreated) {
      // No files or already created — proceed to diagnosis
      setStep("diagnosis");
      // Auto-generate diagnosis questions
      await generateDiagnosisQuestions();
    }
  };

  const handleSkipKB = async () => {
    setKbName("");
    setKbFiles([]);
    setStep("diagnosis");
    await generateDiagnosisQuestions();
  };

  // ── Step 3: Diagnosis ──
  const generateDiagnosisQuestions = async () => {
    setDiagnosisLoading(true);
    setDiagnosisError(null);
    try {
      const questions = await generateDiagnosis({
        exam_name: examName.trim(),
        kb_name: kbName.trim(),
        language: "zh",
      });
      setDiagnosisQuestions(questions);
    } catch (err) {
      setDiagnosisError(err instanceof Error ? err.message : String(err));
    } finally {
      setDiagnosisLoading(false);
    }
  };

  const handleAnswerChange = (questionId: string, answer: string) => {
    setDiagnosisAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  const handleSubmitDiagnosis = async () => {
    setDiagnosisSubmitting(true);
    try {
      // Build answer records with correctness check
      const answers = diagnosisQuestions.map((q) => {
        const userAnswer = diagnosisAnswers[q.question_id] || "";
        const isCorrect = normalizeAnswer(userAnswer) === normalizeAnswer(q.correct_answer);
        return {
          question_id: q.question_id,
          question: q.question,
          correct_answer: q.correct_answer,
          user_answer: userAnswer,
          is_correct: isCorrect,
          error_type: isCorrect ? "" : "incorrect",
          knowledge_point: q.concentration || "",
        };
      });

      const result = await submitDiagnosis({
        exam_name: examName.trim(),
        answers,
      });
      setDiagnosisResult(result);
      setStep("complete");
    } catch (err) {
      setDiagnosisError(err instanceof Error ? err.message : String(err));
    } finally {
      setDiagnosisSubmitting(false);
    }
  };

  const handleFinish = () => {
    onComplete({
      exam_name: examName.trim(),
      exam_date: examDate,
      daily_budget_minutes: budget,
      kb_name: kbName.trim(),
      diagnosis: diagnosisResult,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" />

      {/* Modal */}
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-[var(--border)] bg-[var(--background)] shadow-2xl">
        {/* Step indicator */}
        <div className="flex items-center gap-2 border-b border-[var(--border)] px-6 py-4">
          {STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                  i < currentStepIdx
                    ? "bg-[var(--primary)] text-white"
                    : i === currentStepIdx
                      ? "bg-[var(--primary)]/10 text-[var(--primary)]"
                      : "bg-[var(--muted)] text-[var(--muted-foreground)]"
                }`}
              >
                {i < currentStepIdx ? <Check size={14} /> : i + 1}
              </div>
              <span
                className={`text-xs ${
                  i === currentStepIdx
                    ? "font-medium text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)]"
                }`}
              >
                {t(s.label)}
              </span>
              {i < STEPS.length - 1 && (
                <div className="mx-1 h-px w-4 bg-[var(--border)]" />
              )}
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* ── Step 1: Exam Info ── */}
          {step === "exam_info" && (
            <div className="space-y-4">
              <div className="mb-4 text-center">
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

              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-[var(--foreground)]">
                  <BookOpen size={14} />
                  {t("Exam Name")}
                </label>
                <input
                  type="text"
                  value={examName}
                  onChange={(e) => setExamName(e.target.value)}
                  placeholder={t("e.g. Computer Networks Final Exam")}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]/40"
                  required
                />
              </div>

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
            </div>
          )}

          {/* ── Step 2: KB Upload ── */}
          {step === "kb_upload" && (
            <div className="space-y-4">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-[var(--foreground)]">
                  {t("Create Knowledge Base")}
                </h2>
                <p className="mt-1 text-sm text-[var(--muted-foreground)]">
                  {t("Upload your course materials for more personalized learning")}
                </p>
              </div>

              <div>
                <label className="mb-1.5 text-sm font-medium text-[var(--foreground)]">
                  {t("Knowledge Base Name")}
                </label>
                <input
                  type="text"
                  value={kbName}
                  onChange={(e) => setKbName(e.target.value)}
                  placeholder={t("e.g. Computer Networks")}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]/40"
                />
              </div>

              {/* File upload area */}
              <div>
                <label className="mb-1.5 text-sm font-medium text-[var(--foreground)]">
                  {t("Course Materials (optional)")}
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-[var(--border)] bg-[var(--muted)]/30 px-4 py-6 transition-colors hover:border-[var(--primary)]/40"
                >
                  <Upload size={20} className="text-[var(--muted-foreground)]" />
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {kbFiles.length > 0
                      ? t("{count} file(s) selected", { count: kbFiles.length })
                      : t("Click to upload PDF, DOCX, TXT, MD files")}
                  </span>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.doc,.txt,.md,.pptx,.xlsx"
                  className="hidden"
                  onChange={(e) => setKbFiles(Array.from(e.target.files || []))}
                />
              </div>

              {kbError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300">
                  {kbError}
                </div>
              )}

              {kbCreated && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-800/30 dark:bg-emerald-950/20 dark:text-emerald-300">
                  {t("Knowledge base created successfully")}
                </div>
              )}

              <div className="rounded-lg bg-[var(--muted)]/50 px-3 py-2 text-xs text-[var(--muted-foreground)]">
                <AlertCircle size={12} className="mr-1 inline" />
                {t("Skipping this step will use general knowledge for learning materials. Uploading course materials provides more personalized content.")}
              </div>
            </div>
          )}

          {/* ── Step 3: Diagnosis ── */}
          {step === "diagnosis" && (
            <div className="space-y-4">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-[var(--foreground)]">
                  {t("Diagnostic Assessment")}
                </h2>
                <p className="mt-1 text-sm text-[var(--muted-foreground)]">
                  {t("Answer these questions to assess your current understanding")}
                </p>
              </div>

              {diagnosisLoading && (
                <div className="flex flex-col items-center gap-3 py-10">
                  <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
                  <span className="text-sm text-[var(--muted-foreground)]">
                    {t("Generating diagnostic questions...")}
                  </span>
                </div>
              )}

              {diagnosisError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300">
                  {diagnosisError}
                  <button
                    onClick={generateDiagnosisQuestions}
                    className="ml-2 underline hover:no-underline"
                  >
                    {t("Retry")}
                  </button>
                </div>
              )}

              {!diagnosisLoading && !diagnosisError && diagnosisQuestions.length > 0 && (
                <div className="space-y-4">
                  <div className="text-xs text-[var(--muted-foreground)]">
                    {t("{count} questions", { count: diagnosisQuestions.length })}
                  </div>
                  {diagnosisQuestions.map((q, idx) => (
                    <div
                      key={q.question_id}
                      className="rounded-lg border border-[var(--border)] bg-[var(--secondary)]/30 p-4"
                    >
                      <div className="mb-2 text-sm font-medium text-[var(--foreground)]">
                        {idx + 1}. {q.question}
                      </div>
                      {q.question_type === "choice" && q.options ? (
                        <div className="space-y-1.5">
                          {Object.entries(q.options).map(([key, label]) => (
                            <label
                              key={key}
                              className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm text-[var(--foreground)] hover:bg-[var(--muted)]/50"
                            >
                              <input
                                type="radio"
                                name={q.question_id}
                                value={key}
                                checked={diagnosisAnswers[q.question_id] === key}
                                onChange={() => handleAnswerChange(q.question_id, key)}
                                className="accent-[var(--primary)]"
                              />
                              {label}
                            </label>
                          ))}
                        </div>
                      ) : (
                        <input
                          type="text"
                          value={diagnosisAnswers[q.question_id] || ""}
                          onChange={(e) => handleAnswerChange(q.question_id, e.target.value)}
                          placeholder={t("Your answer")}
                          className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]/40"
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Step 4: Complete ── */}
          {step === "complete" && diagnosisResult && (
            <div className="space-y-4">
              <div className="mb-4 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                  <Check size={24} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <h2 className="text-lg font-semibold text-[var(--foreground)]">
                  {t("Setup Complete")}
                </h2>
              </div>

              {/* Score summary */}
              <div className="rounded-lg border border-[var(--border)] bg-[var(--secondary)]/30 p-4">
                <div className="mb-2 text-sm font-medium text-[var(--foreground)]">
                  {t("Diagnostic Results")}
                </div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <div className="text-2xl font-bold text-[var(--foreground)]">
                      {Math.round(diagnosisResult.overall_score * 100)}%
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)]">{t("Score")}</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-[var(--foreground)]">
                      {diagnosisResult.correct}/{diagnosisResult.total_questions}
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)]">{t("Correct")}</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-[var(--foreground)]">
                      {diagnosisResult.weak_points.length}
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)]">{t("Weak Areas")}</div>
                  </div>
                </div>
              </div>

              {/* Weak points */}
              {diagnosisResult.weak_points.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800/30 dark:bg-amber-950/20">
                  <div className="mb-2 text-sm font-medium text-amber-800 dark:text-amber-300">
                    {t("Areas to Focus On")}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {diagnosisResult.weak_points.map((wp) => (
                      <span
                        key={wp}
                        className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                      >
                        {wp}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Strong points */}
              {diagnosisResult.strong_points.length > 0 && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800/30 dark:bg-emerald-950/20">
                  <div className="mb-2 text-sm font-medium text-emerald-800 dark:text-emerald-300">
                    {t("Your Strengths")}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {diagnosisResult.strong_points.map((sp) => (
                      <span
                        key={sp}
                        className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
                      >
                        {sp}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[var(--border)] px-6 py-4">
          <button
            onClick={() => {
              const idx = STEPS.findIndex((s) => s.key === step);
              if (idx > 0) setStep(STEPS[idx - 1].key);
            }}
            disabled={currentStepIdx === 0}
            className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] hover:bg-[var(--muted)] disabled:invisible"
          >
            <ChevronLeft size={16} />
            {t("Back")}
          </button>

          <div className="flex gap-2">
            {step === "kb_upload" && !kbCreated && (
              <button
                onClick={handleSkipKB}
                className="rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
              >
                {t("Skip")}
              </button>
            )}

            {step === "exam_info" && (
              <button
                onClick={handleExamInfoNext}
                disabled={!examName.trim() || !examDate}
                className="flex items-center gap-1 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {t("Next")}
                <ChevronRight size={16} />
              </button>
            )}

            {step === "kb_upload" && (
              <>
                {!kbCreated ? (
                  <button
                    onClick={handleCreateKB}
                    disabled={kbCreating || !kbName.trim()}
                    className="flex items-center gap-1 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    {kbCreating ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Upload size={16} />
                    )}
                    {kbCreating ? t("Creating...") : t("Create KB")}
                  </button>
                ) : (
                  <button
                    onClick={handleKBNext}
                    className="flex items-center gap-1 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
                  >
                    {t("Next")}
                    <ChevronRight size={16} />
                  </button>
                )}
              </>
            )}

            {step === "diagnosis" && !diagnosisLoading && diagnosisQuestions.length > 0 && (
              <button
                onClick={handleSubmitDiagnosis}
                disabled={diagnosisSubmitting}
                className="flex items-center gap-1 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {diagnosisSubmitting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Check size={16} />
                )}
                {diagnosisSubmitting ? t("Submitting...") : t("Submit Answers")}
              </button>
            )}

            {step === "complete" && (
              <button
                onClick={handleFinish}
                disabled={loading}
                className="flex items-center gap-1 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <BookOpen size={16} />
                )}
                {loading ? t("Setting up...") : t("Start Sprint")}
              </button>
            )}
          </div>
        </div>

        {/* Global error */}
        {error && (
          <div className="border-t border-[var(--border)] bg-rose-50 px-6 py-3 text-sm text-rose-700 dark:bg-rose-950/20 dark:text-rose-300">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

/** Normalize answer for comparison (trim, lowercase). */
function normalizeAnswer(answer: string): string {
  return answer.trim().toLowerCase();
}
