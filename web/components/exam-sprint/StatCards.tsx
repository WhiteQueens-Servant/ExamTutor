"use client";

import { Calendar, Flame, ListChecks, TrendingUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { SprintMeta } from "./types";

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
}

function StatCard({ icon, label, value, sub }: StatCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--secondary)]/30 px-4 py-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--background)]/60 text-[var(--muted-foreground)]">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
          {value}
        </div>
        <div className="text-[11px] text-[var(--muted-foreground)]">{label}</div>
        {sub && (
          <div className="text-[10px] text-[var(--muted-foreground)]/70">{sub}</div>
        )}
      </div>
    </div>
  );
}

export function StatCards({ meta }: { meta: SprintMeta }) {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard
        icon={<ListChecks size={16} />}
        label={t("Today's Tasks")}
        value={`${meta.completed_tasks_today}/${meta.total_tasks_today}`}
      />
      <StatCard
        icon={<TrendingUp size={16} />}
        label={t("Est. Score Boost")}
        value="+12%"
        sub={t("if all completed")}
      />
      <StatCard
        icon={<Flame size={16} />}
        label={t("Streak")}
        value={`${meta.streak} ${t("days")}`}
      />
      <StatCard
        icon={<Calendar size={16} />}
        label={t("Remaining")}
        value={`${meta.days_remaining} ${t("days")}`}
        sub={meta.exam_date}
      />
    </div>
  );
}
