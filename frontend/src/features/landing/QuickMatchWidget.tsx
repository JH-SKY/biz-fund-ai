"use client";

/**
 * QuickMatchWidget — 랜딩의 '퀵 선택' 섹션.
 *
 * 스펙 (기획서 §2-②)
 *  - [지역 선택] + [업종 선택] + [조회하기]
 *  - 둘 중 하나라도 비어있으면 '모두 선택해주세요' 인라인 안내
 *  - 값은 sessionStorage('biz_up_landing_filter')에 저장 → 로그인에서 돌아와도 복구
 *  - 제출 시 부모에게 onSubmit({ region, industry }) 전달 → 결과 Modal 오픈
 */

import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Label, FieldHint } from "@/components/ui/label";
import { REGION_OPTIONS } from "@/constants/regions";
import { INDUSTRY_OPTIONS } from "@/constants/industries";

const STORAGE_KEY = "biz_up_landing_filter";

export interface LandingFilter {
  region: string;
  industry: string;
}

export function loadLandingFilter(): LandingFilter {
  if (typeof window === "undefined") return { region: "", industry: "" };
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return { region: "", industry: "" };
    const parsed = JSON.parse(raw) as LandingFilter;
    return {
      region: parsed.region ?? "",
      industry: parsed.industry ?? "",
    };
  } catch {
    return { region: "", industry: "" };
  }
}

export function saveLandingFilter(filter: LandingFilter) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(filter));
}

interface QuickMatchWidgetProps {
  onSubmit: (filter: LandingFilter) => void;
}

export function QuickMatchWidget({ onSubmit }: QuickMatchWidgetProps) {
  const [region, setRegion] = useState("");
  const [industry, setIndustry] = useState("");
  const [error, setError] = useState<string | null>(null);

  // 이전 선택 복구 (뒤로가기 시나리오)
  useEffect(() => {
    const saved = loadLandingFilter();
    if (saved.region) setRegion(saved.region);
    if (saved.industry) setIndustry(saved.industry);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!region || !industry) {
      setError("지역과 업종을 모두 선택해주세요.");
      return;
    }
    setError(null);
    const filter = { region, industry };
    saveLandingFilter(filter);
    onSubmit(filter);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-2xl rounded-2xl border border-surface-border bg-surface p-5 shadow-card sm:p-6"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="landing-region" required>
            지역
          </Label>
          <Select
            id="landing-region"
            value={region}
            onChange={(e) => {
              setRegion(e.target.value);
              setError(null);
            }}
            placeholder="시·도 선택"
            options={REGION_OPTIONS}
            invalid={!!error && !region}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="landing-industry" required>
            업종
          </Label>
          <Select
            id="landing-industry"
            value={industry}
            onChange={(e) => {
              setIndustry(e.target.value);
              setError(null);
            }}
            placeholder="업종 선택"
            options={INDUSTRY_OPTIONS}
            invalid={!!error && !industry}
          />
        </div>
      </div>

      {error && <FieldHint tone="error">{error}</FieldHint>}

      <Button type="submit" variant="primary" size="lg" className="mt-5 w-full">
        <Search />
        지금 내 정책자금 확인하기
      </Button>
      <p className="mt-3 text-center text-xs text-ink-tertiary">
        · 로그인 없이 공고 건수만 미리 확인할 수 있어요
      </p>
    </form>
  );
}
