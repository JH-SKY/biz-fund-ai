"use client";

/**
 * 사업장 정보 탭 — 상호명·사업자번호·지역·업종 등 수정 폼 + 정보 완성도 프로그레스.
 */

import * as React from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { REGION_OPTIONS } from "@/constants/regions";
import { INDUSTRY_OPTIONS } from "@/constants/industries";
import { useProfileBusiness, useUpdateBusiness } from "@/hooks/useProfile";
import type { BusinessUpdateRequest } from "@/types";

function ProfileScore({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const color =
    pct >= 80
      ? "bg-success-500"
      : pct >= 50
      ? "bg-accent-500"
      : "bg-danger-400";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-ink">정보 완성도</span>
        <span className="numeric font-bold text-ink">{pct}%</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-surface-subtle">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {pct < 80 && (
        <p className="text-xs text-ink-secondary">
          정보를 더 채우면 정책 매칭 정확도가 높아져요.
        </p>
      )}
    </div>
  );
}

export function BusinessInfoTab() {
  const { data: biz, isLoading } = useProfileBusiness();
  const updateBiz = useUpdateBusiness();

  const [form, setForm] = React.useState<BusinessUpdateRequest>({});
  const [saved, setSaved] = React.useState(false);

  // biz 로드되면 폼 초기화
  React.useEffect(() => {
    if (!biz) return;
    setForm({
      biz_name: biz.biz_name,
      representative_name: biz.representative_name ?? "",
      region_sido: biz.region_sido ?? "",
      region_sigungu: biz.region_sigungu ?? "",
      establishment_date: biz.establishment_date ?? "",
      ksic_code: biz.ksic_code ?? "",
      has_patent: biz.has_patent,
      is_female_ent: biz.is_female_ent,
      is_ventured: biz.is_ventured,
    });
  }, [biz]);

  function patch<K extends keyof BusinessUpdateRequest>(
    key: K,
    value: BusinessUpdateRequest[K]
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await updateBiz.mutateAsync(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded-lg bg-surface-subtle" />
        ))}
      </div>
    );
  }

  if (!biz) {
    return (
      <p className="text-sm text-ink-secondary">
        사업장 정보를 불러올 수 없습니다.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">정보 완성도</CardTitle>
        </CardHeader>
        <CardContent>
          <ProfileScore score={biz.profile_score} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">기본 정보</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="biz_name">상호명</Label>
              <Input
                id="biz_name"
                value={form.biz_name ?? ""}
                onChange={(e) => patch("biz_name", e.target.value)}
                placeholder="예) 비즈업 주식회사"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="biz_no">사업자등록번호</Label>
              <Input
                id="biz_no"
                value={biz.biz_no ?? ""}
                disabled
                className="bg-surface-subtle"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="representative_name">대표자명</Label>
            <Input
              id="representative_name"
              value={form.representative_name ?? ""}
              onChange={(e) => patch("representative_name", e.target.value)}
              placeholder="대표자 성함"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="region_sido">지역 (시·도)</Label>
              <Select
                id="region_sido"
                value={form.region_sido ?? ""}
                onChange={(e) => patch("region_sido", e.target.value)}
                options={REGION_OPTIONS.filter((r) => r.value !== "ALL")}
                placeholder="시·도 선택"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="region_sigungu">시·군·구</Label>
              <Input
                id="region_sigungu"
                value={form.region_sigungu ?? ""}
                onChange={(e) => patch("region_sigungu", e.target.value)}
                placeholder="예) 강남구"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ksic_code">업종 (KSIC)</Label>
              <Select
                id="ksic_code"
                value={form.ksic_code ?? ""}
                onChange={(e) => patch("ksic_code", e.target.value)}
                options={INDUSTRY_OPTIONS}
                placeholder="업종 선택"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="establishment_date">설립일</Label>
              <Input
                id="establishment_date"
                type="date"
                value={form.establishment_date ?? ""}
                onChange={(e) => patch("establishment_date", e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">추가 속성</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {(
              [
                { key: "has_patent", label: "특허 보유" },
                { key: "is_female_ent", label: "여성기업" },
                { key: "is_ventured", label: "벤처기업" },
              ] as const
            ).map(({ key, label }) => (
              <label
                key={key}
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-surface-border px-4 py-2.5 text-sm font-medium transition-colors has-[:checked]:border-primary-600 has-[:checked]:bg-primary-50 has-[:checked]:text-primary-700"
              >
                <input
                  type="checkbox"
                  checked={Boolean(form[key])}
                  onChange={(e) => patch(key, e.target.checked)}
                  className="sr-only"
                />
                {label}
              </label>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-end gap-3">
        {saved && (
          <span className="text-sm font-medium text-success-600">
            저장되었습니다 ✓
          </span>
        )}
        <Button
          type="submit"
          loading={updateBiz.isPending}
          className="gap-2"
        >
          <Save className="h-4 w-4" />
          저장하기
        </Button>
      </div>
    </form>
  );
}
