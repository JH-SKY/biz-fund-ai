"use client";

/**
 * 사업장 신호등 위젯 — 현재 사업장의 '신청 준비 상태'를 즉각 전달.
 *
 * 판정 규칙 (점수 기반 — 서류 여부와 무관)
 *  - GREEN  : score >= 70
 *  - YELLOW : score >= 40 (재무정보 미입력 포함)
 *  - RED    : score < 40
 *
 * 최신 진단 점수(`latestDiagnosisScore`)가 있으면 그것을 우선 반영 (더 정밀).
 */

import { AlertCircle, CheckCircle2, Sparkles } from "lucide-react";

import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { TrafficLightBadge } from "@/components/shared/TrafficLightBadge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { BusinessInfo } from "@/types";

interface Props {
  business?: BusinessInfo | null;
  latestDiagnosisScore?: number | null;
  isLoading?: boolean;
}

type Light = "green" | "yellow" | "red";

function computeLight(score: number): {
  level: Light;
  reasons: string[];
  advice: string[];
} {
  const reasons: string[] = [];
  const advice: string[] = [];

  let level: Light = "green";
  if (score < 40) level = "red";
  else if (score < 70) level = "yellow";

  if (score < 60) {
    reasons.push(`프로필 점수 ${score}점 — 기본 정보를 더 채워주세요`);
    advice.push("사업자번호·업종·지역·창업일·대표자명 등을 입력하면 점수가 올라갑니다.");
  } else if (score < 70) {
    reasons.push(`프로필 점수 ${score}점 — 재무정보 미입력`);
    advice.push("재무정보(연매출·부채 등)를 입력하면 100점 만점이 되고 맞춤 정책 확률이 정확해집니다.");
  } else if (score < 100) {
    reasons.push(`프로필 점수 ${score}점 — 가점 항목을 보완해 보세요`);
    advice.push("특허·벤처·여성기업 인증 여부를 추가하면 점수가 더 올라갑니다.");
  }

  if (reasons.length === 0) {
    reasons.push("모든 정보가 입력되었습니다.");
    advice.push("지금이 신청 적기에요. 원픽 카드에서 바로 신청하세요.");
  }

  return { level, reasons, advice };
}

export function TrafficLightWidget({
  business,
  latestDiagnosisScore,
  isLoading,
}: Props) {
  if (isLoading || !business) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-32 rounded bg-surface-subtle" />
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded bg-surface-subtle" />
        </CardContent>
      </Card>
    );
  }

  const score = Math.round(
    latestDiagnosisScore ?? business.profile_score ?? 0
  );
  const { level, reasons, advice } = computeLight(score);

  const LightIcon =
    level === "green" ? CheckCircle2 : level === "yellow" ? Sparkles : AlertCircle;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle>사업장 신호등</CardTitle>
            <CardDescription>
              신청 준비 상태를 한눈에 확인하세요.
            </CardDescription>
          </div>
          <TrafficLightBadge status={level} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-6">
          <ScoreGauge
            score={score}
            size="md"
            label={latestDiagnosisScore != null ? "진단 점수" : "프로필 점수"}
          />
          <div className="flex-1 space-y-3">
            <section>
              <h3 className="text-sm font-semibold text-ink">
                <LightIcon className="-mt-0.5 mr-1 inline h-4 w-4" />
                진단 근거
              </h3>
              <ul className="mt-1 space-y-1 text-sm text-ink-secondary">
                {reasons.map((r) => (
                  <li key={r} className="flex gap-1.5">
                    <span className="text-ink-tertiary">·</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h3 className="text-sm font-semibold text-ink">
                💡 컨설팅 가이드
              </h3>
              <ul className="mt-1 space-y-1 text-sm text-ink-secondary">
                {advice.map((a) => (
                  <li key={a} className="flex gap-1.5">
                    <span className="text-ink-tertiary">·</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
