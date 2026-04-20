"use client";

/**
 * SimulatorCard — 조건 변경 시뮬레이션 결과 카드.
 * .cursorrules §7-3
 *  - before/after 점수 비교 (CSS 바)
 *  - 점수 변화 badge
 *  - insights 목록
 */

import { TrendingUp, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AgentSimulationReport } from "@/types";

interface Props {
  report: AgentSimulationReport;
}

function ScoreBar({
  label,
  score,
  color,
}: {
  label: string;
  score: number;
  color: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-ink-secondary">{label}</span>
        <span className={cn("font-bold numeric", color)}>
          {Math.round(score)}점
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-surface-subtle">
        <div
          className={cn("h-full rounded-full transition-all duration-700", color === "text-success-600" ? "bg-success-500" : "bg-primary-500")}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
    </div>
  );
}

export function SimulatorCard({ report }: Props) {
  const { original_score, virtual_score, diff, insights } = report;
  const isPositive = diff >= 0;

  return (
    <Card className="w-full overflow-hidden border-success-200">
      <div className="flex items-center gap-2 bg-success-500 px-4 py-2.5">
        <TrendingUp className="h-4 w-4 text-white" />
        <span className="text-sm font-bold text-white">시뮬레이션 결과</span>
      </div>

      <CardContent className="p-4 space-y-4">
        {/* 점수 변화 요약 */}
        <div className="flex items-center justify-center gap-4">
          <div className="text-center">
            <p className="text-xs text-ink-tertiary">현재</p>
            <p className="numeric text-3xl font-bold text-ink">
              {Math.round(original_score)}
            </p>
          </div>
          <div className="flex flex-col items-center gap-0.5">
            <div
              className={cn(
                "rounded-full px-3 py-1 text-sm font-bold numeric",
                isPositive
                  ? "bg-success-50 text-success-700"
                  : "bg-danger-50 text-danger-700"
              )}
            >
              {isPositive ? "+" : ""}
              {Math.round(diff)}점
            </div>
            <span className="text-lg text-ink-tertiary">→</span>
          </div>
          <div className="text-center">
            <p className="text-xs text-ink-tertiary">가상</p>
            <p
              className={cn(
                "numeric text-3xl font-bold",
                isPositive ? "text-success-600" : "text-danger-600"
              )}
            >
              {Math.round(virtual_score)}
            </p>
          </div>
        </div>

        {/* 막대 비교 */}
        <div className="space-y-2">
          <ScoreBar
            label="현재 점수"
            score={original_score}
            color="text-primary-700"
          />
          <ScoreBar
            label="가상 점수"
            score={virtual_score}
            color="text-success-600"
          />
        </div>

        {/* 핵심 인사이트 */}
        {insights && insights.length > 0 && (
          <div className="space-y-1.5 rounded-xl bg-surface-muted p-3">
            <p className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-primary-700">
              <Zap className="h-3 w-3" /> 핵심 인사이트
            </p>
            <ul className="space-y-1">
              {insights.slice(0, 3).map((ins, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-ink-secondary">
                  <span className="mt-0.5 shrink-0 font-bold text-primary-500">
                    {i + 1}.
                  </span>
                  {ins}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
