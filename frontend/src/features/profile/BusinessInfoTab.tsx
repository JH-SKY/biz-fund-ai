"use client";

/**
 * 사업장 기본 정보 수정 탭.
 */

import * as React from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  REGION_OPTIONS,
  getSigunguOptions,
  isValidSigungu,
} from "@/constants/regions";
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
          정보를 더 채우면 정책 매칭 정확도가 높아집니다.
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

  const sigunguOptions = React.useMemo(
    () => getSigunguOptions(form.region_sido ?? ""),
    [form.region_sido]
  );

  React.useEffect(() => {
    if (!biz) return;

    setForm({
      biz_name: biz.biz_name,
      representative_name: biz.representative_name ?? "",
      region_sido: biz.region_sido ?? "",
      region_sigungu: biz.region_sigungu ?? "",
      establishment_date: biz.establishment_date ?? "",
      ksic_code: biz.ksic_code ?? biz.sector_code ?? "",
      sector_code: biz.sector_code ?? biz.ksic_code ?? "",
      has_patent: biz.has_patent,
      is_female_ent: biz.is_female_ent,
      is_ventured: biz.is_ventured,
    });
  }, [biz]);

  React.useEffect(() => {
    if (!form.region_sido || !form.region_sigungu) return;
    if (isValidSigungu(form.region_sido, form.region_sigungu)) return;

    setForm((prev) => ({
      ...prev,
      region_sigungu: "",
    }));
  }, [form.region_sido, form.region_sigungu]);

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
          <div
            key={i}
            className="h-12 animate-pulse rounded-lg bg-surface-subtle"
          />
        ))}
      </div>
    );
  }

  if (!biz) {
    return (
      <p className="text-sm text-ink-secondary">
        사업장 정보를 불러오지 못했습니다.
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
                placeholder="예: 비즈업 주식회사"
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
              <Label htmlFor="region_sido">지역(시도)</Label>
              <Select
                id="region_sido"
                value={form.region_sido ?? ""}
                onChange={(e) => {
                  patch("region_sido", e.target.value);
                  patch("region_sigungu", "");
                }}
                options={REGION_OPTIONS.filter((region) => region.value !== "ALL")}
                placeholder="시도 선택"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="region_sigungu">시군구</Label>
              <Select
                id="region_sigungu"
                value={form.region_sigungu ?? ""}
                onChange={(e) => patch("region_sigungu", e.target.value)}
                options={sigunguOptions}
                disabled={!form.region_sido}
                placeholder={
                  form.region_sido ? "시군구 선택" : "먼저 시도를 선택해 주세요"
                }
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ksic_code">업종 (KSIC)</Label>
              <Select
                id="ksic_code"
                value={form.ksic_code ?? form.sector_code ?? ""}
                onChange={(e) => {
                  patch("ksic_code", e.target.value);
                  patch("sector_code", e.target.value);
                }}
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
          <CardTitle className="text-base">추가 특성</CardTitle>
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
            저장되었습니다.
          </span>
        )}
        <Button type="submit" loading={updateBiz.isPending} className="gap-2">
          <Save className="h-4 w-4" />
          저장하기
        </Button>
      </div>
    </form>
  );
}
