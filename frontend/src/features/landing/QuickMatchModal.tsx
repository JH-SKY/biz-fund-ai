"use client";

/**
 * QuickMatchModal — 퀵 조회 결과 팝업.
 *
 * 스펙 (기획서 §2-②)
 *  - "(지역명) (업종명) 신청 가능 금액: (금액)" 노출
 *  - 실제 집계는 백엔드 엔드포인트가 확정되기 전이므로 룩업 테이블로 모킹
 *    → 추후 GET /public/policies/summary?region=&industry= 로 교체
 *  - CTA: "지금 로그인하고 분석받기" → /login 으로 이동
 */

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { getRegionLabel } from "@/constants/regions";
import { getIndustryLabel } from "@/constants/industries";

interface QuickMatchModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  region: string;
  industry: string;
}

/** TEMP 모킹: 업종·지역 조합별 대략치. 추후 API 로 교체. */
function estimateSummary(region: string, industry: string) {
  const base = (region === "ALL" ? 47 : 12) + (industry.charCodeAt(0) % 9);
  const amount = base * 11_0000_0000; // 원
  return {
    available_count: base,
    total_amount: amount,
    top_category: ["융자", "보조금", "보증", "R&D"][base % 4],
  };
}

export function QuickMatchModal({
  open,
  onOpenChange,
  region,
  industry,
}: QuickMatchModalProps) {
  const regionLabel = getRegionLabel(region);
  const industryLabel = getIndustryLabel(industry);
  const summary = estimateSummary(region, industry);

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="지금 신청 가능한 정책자금"
      description={`${regionLabel} · ${industryLabel} 기준`}
      footer={
        <>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            닫기
          </Button>
          <Link href="/login">
            <Button variant="primary">
              지금 로그인하고 분석받기
              <ArrowRight />
            </Button>
          </Link>
        </>
      }
    >
      <div className="space-y-5">
        <div className="rounded-xl bg-primary-50 p-5 text-center">
          <p className="text-xs font-semibold text-primary-700">
            신청 가능한 공고
          </p>
          <p className="mt-1 text-4xl font-bold text-primary-700 numeric">
            {summary.available_count}
            <span className="text-lg font-semibold text-primary-500"> 건</span>
          </p>
          <p className="mt-3 text-xs text-ink-tertiary">예상 지원 규모</p>
          <p className="mt-1 text-2xl font-bold text-ink numeric">
            약 ₩ {summary.total_amount.toLocaleString("ko-KR")}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2">
          <Badge variant="success">신청 가능</Badge>
          <Badge variant="primary">{summary.top_category} 중심</Badge>
          <Badge variant="accent">
            <Sparkles className="h-3 w-3" />
            AI 맞춤 분석 대상
          </Badge>
        </div>

        <p className="text-center text-sm text-ink-secondary">
          로그인하시면 비즈몽 AI 가 사업장 조건을 반영해
          <br className="hidden sm:block" />
          <span className="font-semibold text-ink">
            {" "}신청 가능성 높은 TOP 정책
          </span>
          을 맞춤 추천해드려요.
        </p>
      </div>
    </Dialog>
  );
}
