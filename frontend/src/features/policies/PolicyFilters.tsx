"use client";

/**
 * 정책 리스트 공용 필터 바.
 * - 키워드 검색
 * - 지역 / 카테고리 / 기관 Select
 * - [초기화] 버튼으로 일괄 해제
 * - 변경 시 onChange 콜백 (debounce 150ms for keyword)
 */

import { useEffect, useState } from "react";
import { RotateCcw, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { REGION_OPTIONS } from "@/constants/regions";
import { AGENCY_OPTIONS, POLICY_CATEGORIES } from "@/constants/agencies";

export interface PolicyFilterState {
  keyword: string;
  region: string;
  category: string;
  agency: string;
}

const EMPTY: PolicyFilterState = {
  keyword: "",
  region: "",
  category: "",
  agency: "",
};

interface PolicyFiltersProps {
  value: PolicyFilterState;
  onChange: (next: PolicyFilterState) => void;
}

export function PolicyFilters({ value, onChange }: PolicyFiltersProps) {
  const [draftKeyword, setDraftKeyword] = useState(value.keyword);

  // 외부 상태 → 로컬 드래프트 동기화 (초기화 등 외부 변경 반영)
  useEffect(() => setDraftKeyword(value.keyword), [value.keyword]);

  // 키워드 150ms 디바운스
  useEffect(() => {
    if (draftKeyword === value.keyword) return;
    const t = setTimeout(() => onChange({ ...value, keyword: draftKeyword }), 150);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftKeyword]);

  const hasAny =
    value.keyword || value.region || value.category || value.agency;

  return (
    <div className="rounded-xl border border-surface-border bg-surface p-4 shadow-card sm:p-5">
      <div className="flex flex-col gap-3">
        <Input
          leftIcon={<Search className="h-4 w-4" />}
          placeholder="공고 명칭, 본문 키워드로 검색"
          value={draftKeyword}
          onChange={(e) => setDraftKeyword(e.target.value)}
          aria-label="정책 검색"
        />

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div className="flex flex-col gap-1">
            <Label className="text-xs">지역</Label>
            <Select
              options={REGION_OPTIONS}
              placeholder="전체 지역"
              value={value.region}
              onChange={(e) => onChange({ ...value, region: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-xs">카테고리</Label>
            <Select
              options={POLICY_CATEGORIES}
              placeholder="전체 카테고리"
              value={value.category}
              onChange={(e) => onChange({ ...value, category: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-xs">기관</Label>
            <Select
              options={AGENCY_OPTIONS}
              placeholder="전체 기관"
              value={value.agency}
              onChange={(e) => onChange({ ...value, agency: e.target.value })}
            />
          </div>
        </div>

        {hasAny && (
          <div className="flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onChange({ ...EMPTY })}
              aria-label="필터 초기화"
            >
              <RotateCcw />
              필터 초기화
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export const EMPTY_POLICY_FILTER: PolicyFilterState = EMPTY;
