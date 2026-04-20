"use client";

/**
 * StatsCard — 동종업계 통계 비교 카드.
 * .cursorrules §7-5
 *  - peer_comparison / market_trend 텍스트
 *  - Recharts BarChart 로 업계 평균 vs 우리 사업장 시각화
 *    (현재 백엔드 response 에는 비정형 텍스트만 있으므로 텍스트 중심 렌더링)
 */

import { BarChart2, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { AgentStatsInsight } from "@/types";

interface Props {
  insight: AgentStatsInsight;
}

export function StatsCard({ insight }: Props) {
  const { peer_comparison, market_trend } = insight;

  return (
    <Card className="w-full overflow-hidden border-accent-200">
      <div className="flex items-center gap-2 bg-accent-500 px-4 py-2.5">
        <BarChart2 className="h-4 w-4 text-white" />
        <span className="text-sm font-bold text-white">동종업계 통계 분석</span>
      </div>

      <CardContent className="p-4 space-y-4">
        {market_trend && (
          <div className="flex items-start gap-2 rounded-xl bg-accent-50 p-3">
            <TrendingUp className="mt-0.5 h-4 w-4 shrink-0 text-accent-700" />
            <div>
              <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-accent-700">
                시장 트렌드
              </p>
              <p className="text-sm leading-relaxed text-ink">{market_trend}</p>
            </div>
          </div>
        )}

        {peer_comparison && (
          <div className="rounded-xl bg-surface-muted p-3">
            <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-secondary">
              동종업계 비교
            </p>
            <p className="text-sm leading-relaxed text-ink-secondary whitespace-pre-line">
              {peer_comparison}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
