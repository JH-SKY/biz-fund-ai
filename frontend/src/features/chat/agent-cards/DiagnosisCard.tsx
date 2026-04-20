"use client";

/**
 * DiagnosisCard — 정책자금 진단 결과 카드.
 * .cursorrules §7-2
 *  - 원형 점수 게이지 (ScoreGauge 재사용)
 *  - 카테고리 점수 막대 (tech/employment/stability — 현재 백엔드 미지원, 플레이스홀더)
 *  - 추천 1순위 + 매칭 건수
 *  - AI 어드바이스
 *  - [시뮬레이션해보기] CTA
 */

import Link from "next/link";
import { BarChart2, Lightbulb, Trophy } from "lucide-react";
import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { AgentDiagnosisReport } from "@/types";

interface Props {
  report: AgentDiagnosisReport;
}

export function DiagnosisCard({ report }: Props) {
  const { score, top_policy, advice, total_candidates } = report;
  const scoreColor =
    score >= 70
      ? "text-success-600"
      : score >= 40
      ? "text-accent-700"
      : "text-danger-600";

  return (
    <Card className="w-full overflow-hidden border-primary-100">
      {/* 헤더 */}
      <div className="flex items-center gap-2 bg-primary-600 px-4 py-2.5">
        <BarChart2 className="h-4 w-4 text-white" />
        <span className="text-sm font-bold text-white">정책자금 진단 결과</span>
      </div>

      <CardContent className="p-4">
        {/* 게이지 + 요약 */}
        <div className="flex items-center gap-5">
          <ScoreGauge score={score} size="md" label="적합도" />
          <div className="flex-1 space-y-1">
            <p className={`text-2xl font-bold numeric ${scoreColor}`}>
              {Math.round(score)}
              <span className="text-sm text-ink-tertiary"> / 100</span>
            </p>
            <p className="text-xs text-ink-secondary">
              매칭된 정책:{" "}
              <span className="font-bold text-primary-700 numeric">
                {total_candidates}개
              </span>
            </p>
          </div>
        </div>

        {/* 추천 1순위 */}
        {top_policy && (
          <div className="mt-4 flex items-start gap-2 rounded-xl bg-accent-50 p-3">
            <Trophy className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" />
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wide text-accent-700">
                추천 1순위
              </p>
              <p className="text-sm font-semibold text-ink">{top_policy}</p>
            </div>
          </div>
        )}

        {/* AI 어드바이스 */}
        {advice && (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-surface-muted p-3">
            <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-primary-500" />
            <p className="text-xs leading-relaxed text-ink-secondary">{advice}</p>
          </div>
        )}

        {/* CTA */}
        <div className="mt-4 flex gap-2">
          <Button asChild variant="primary" size="sm" className="flex-1">
            <Link href="/policies/matching">맞춤 정책 보기</Link>
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="flex-1"
            onClick={() => {}}
          >
            시뮬레이션해보기
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
