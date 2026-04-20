"use client";

/**
 * ScoreGauge — 0~100 점수를 원형 게이지로 시각화.
 *
 * 색상 규칙 (.cursorrules §3.2)
 *  - 70 이상 → 녹색 (#10B981 / success)
 *  - 40 이상 → 주황 (#F59E0B / accent)
 *  - 그 외   → 빨강 (#EF4444 / danger)
 *
 * 구현: Recharts `RadialBarChart` — 이미 package.json 의 `recharts` 의존성.
 */

import { useMemo } from "react";
import {
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
} from "recharts";

import { cn } from "@/lib/utils";

interface Props {
  score: number; // 0~100
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

const SIZE_MAP: Record<
  "sm" | "md" | "lg",
  { wrapper: string; value: string; label: string }
> = {
  sm: { wrapper: "h-24 w-24", value: "text-xl", label: "text-[10px]" },
  md: { wrapper: "h-32 w-32", value: "text-3xl", label: "text-xs" },
  lg: { wrapper: "h-40 w-40", value: "text-4xl", label: "text-sm" },
};

export function ScoreGauge({ score, size = "md", label, className }: Props) {
  const clamped = Math.min(100, Math.max(0, Math.round(score)));
  const color = useMemo(() => {
    if (clamped >= 70) return "#10B981";
    if (clamped >= 40) return "#F59E0B";
    return "#EF4444";
  }, [clamped]);

  const data = [{ name: "score", value: clamped, fill: color }];
  const dims = SIZE_MAP[size];

  return (
    <div className={cn("relative", dims.wrapper, className)}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          innerRadius="75%"
          outerRadius="100%"
          barSize={10}
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            background={{ fill: "#F1F5F9" }}
            dataKey="value"
            cornerRadius={20}
            angleAxisId={0}
          />
        </RadialBarChart>
      </ResponsiveContainer>

      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={cn("font-bold text-ink numeric leading-none", dims.value)}
          style={{ color }}
        >
          {clamped}
        </span>
        <span className={cn("mt-1 text-ink-tertiary", dims.label)}>
          {label ?? "/ 100"}
        </span>
      </div>
    </div>
  );
}
