"use client";

/**
 * 혜택 수준 인포그래픽 — 유사업종/매출 규모 대비 나의 정책 수혜 수준을 비교 시각화.
 *
 * NOTE:
 *  현재 백엔드에는 전용 비교 집계 API 가 없어 (stats agent 로직 존재),
 *  대시보드 초기 구현에서는 '매칭 점수 평균' 과 '피어 평균(Mock)' 비교를 보여준다.
 *  추후 `/api/v1/businesses/{id}/benefit-level` 등이 생기면 props 를 교체하면 된다.
 */

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, XAxis } from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Props {
  myAvgScore: number | null; // 내 추천 정책 평균 매칭 점수
  peerAvgScore?: number; // 동종업계 평균 (Mock)
  sectorLabel?: string;
}

export function BenefitLevelCard({
  myAvgScore,
  peerAvgScore = 58,
  sectorLabel = "동종업계",
}: Props) {
  const me = myAvgScore ?? 0;
  const gap = Math.round(me - peerAvgScore);

  const data = [
    { label: sectorLabel, value: peerAvgScore, fill: "#CBD5E1" },
    { label: "우리 사업장", value: Math.round(me), fill: "#2563EB" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>혜택 수준 비교</CardTitle>
        <CardDescription>
          사장님의 매칭 점수를 {sectorLabel} 평균과 비교했어요.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {myAvgScore == null ? (
          <p className="text-sm text-ink-tertiary">
            추천 데이터가 준비되면 업계 평균과의 비교가 표시됩니다.
          </p>
        ) : (
          <>
            <div className="flex items-center gap-2">
              {gap >= 0 ? (
                <Badge variant="success">
                  ↑ {gap}점 높아요
                </Badge>
              ) : (
                <Badge variant="warning">↓ {Math.abs(gap)}점 낮아요</Badge>
              )}
              <span className="text-xs text-ink-tertiary">
                (내 평균 매칭점수 기준)
              </span>
            </div>

            <div className="h-28 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} barCategoryGap="35%">
                  <CartesianGrid
                    vertical={false}
                    strokeDasharray="2 4"
                    stroke="#E2E8F0"
                  />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#475569", fontSize: 12 }}
                  />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
