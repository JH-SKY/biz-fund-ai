"use client";

import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  tone?: "primary" | "success" | "warning" | "danger" | "neutral";
  isLoading?: boolean;
}

const TONES: Record<NonNullable<StatCardProps["tone"]>, string> = {
  primary: "bg-primary-50 text-primary-700",
  success: "bg-success-50 text-success-600",
  warning: "bg-accent-50 text-accent-700",
  danger: "bg-danger-50 text-danger-600",
  neutral: "bg-surface-subtle text-ink-secondary",
};

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "primary",
  isLoading = false,
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start gap-4 p-5">
        {Icon && (
          <div
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg",
              TONES[tone]
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-tertiary">
            {label}
          </p>
          {isLoading ? (
            <div className="mt-2 h-7 w-20 animate-pulse rounded bg-surface-subtle" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-ink numeric">{value}</p>
          )}
          {hint && !isLoading && (
            <p className="mt-1 text-xs text-ink-secondary">{hint}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
