"use client";

/**
 * [PAGE] 정밀진단 — /diagnosis
 *
 * 흐름:
 *   1. GET /diagnoses/prepare → 기존 재무 데이터 사전 채움
 *   2. 사용자 입력 (DiagnosisFinalInputs)
 *   3. POST /diagnoses → 진단 결과 표시
 *   4. GET /diagnoses/:id → AI 코멘트 로드
 */

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, ChevronDown, Loader2 } from "lucide-react";

import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { TrafficLightBadge } from "@/components/shared/TrafficLightBadge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  useDiagnosisDetail,
  useExecuteDiagnosis,
  usePrepareDiagnosis,
} from "@/hooks/useDiagnosis";
import type { ExecuteDiagnosisResponse } from "@/types";
import { cn } from "@/lib/utils";

const GRADE_LABEL: Record<string, string> = {
  EXCELLENT: "우수",
  GOOD: "양호",
  NORMAL: "보통",
  RISK: "위험",
};

const GRADE_COLOR: Record<string, string> = {
  EXCELLENT: "bg-green-100 text-green-800",
  GOOD: "bg-blue-100 text-blue-800",
  NORMAL: "bg-yellow-100 text-yellow-800",
  RISK: "bg-red-100 text-red-800",
};

const FUNDING_PURPOSE_OPTIONS = [
  { value: "", label: "선택 안 함" },
  { value: "운영자금", label: "운영자금 — 인건비·재료비 등 일상 운영" },
  { value: "시설자금", label: "시설자금 — 설비·인테리어·장비 구입" },
  { value: "대환자금", label: "대환자금 — 고금리 대출 갈아타기" },
  { value: "창업자금", label: "창업자금 — 사업 시작 초기 비용" },
  { value: "R&D자금", label: "R&D자금 — 연구·개발·특허 관련" },
];

const TAX_TYPE_OPTIONS = [
  { key: "national_tax", label: "국세 (부가세·법인세·소득세 등)" },
  { key: "local_tax", label: "지방세 (재산세·취득세 등)" },
  { key: "4대보험", label: "4대 보험료 미납" },
];

/** 숫자에 천 단위 콤마 삽입 */
function formatComma(val: string): string {
  const digits = val.replace(/[^0-9]/g, "");
  if (!digits) return "";
  return Number(digits).toLocaleString("ko-KR");
}

/** 콤마 제거 후 숫자 반환 */
function parseComma(val: string): number | null {
  const digits = val.replace(/[^0-9]/g, "");
  return digits ? Number(digits) : null;
}

export default function DiagnosisPage() {
  const prepareQ = usePrepareDiagnosis();
  const executeMut = useExecuteDiagnosis();

  const [result, setResult] = useState<ExecuteDiagnosisResponse | null>(null);
  const [form, setForm] = useState({
    annual_revenue: "",   // 표시용 콤마 문자열
    total_debt: "",       // 표시용 콤마 문자열
    employee_count: "",
    has_tax_arrears: false,
    tax_types: { national_tax: false, local_tax: false, "4대보험": false },
    tax_amount: "",       // 체납 금액 (콤마 문자열)
    has_patent: false,
    is_female_ent: false,
    is_ventured: false,
    funding_purpose: "",
  });

  const detailQ = useDiagnosisDetail(result?.diagnosis_id ?? null);

  // 사전 채움: prepare 데이터가 로드되면 form에 반영
  const snap = prepareQ.data?.current_snapshot;
  const [prefilled, setPrefilled] = useState(false);
  if (snap && !prefilled && !result) {
    setForm((prev) => ({
      ...prev,
      annual_revenue: snap.revenue != null ? Number(snap.revenue).toLocaleString("ko-KR") : "",
      employee_count: snap.employee_count != null ? String(snap.employee_count) : "",
    }));
    setPrefilled(true);
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await executeMut.mutateAsync({
      year: new Date().getFullYear(),
      use_ai_analysis: false,
      final_inputs: {
        has_tax_arrears: form.has_tax_arrears,
        annual_revenue: parseComma(form.annual_revenue),
        total_debt: parseComma(form.total_debt),
        debt_ratio: null,
        employee_count: Number(form.employee_count) || 0,
        has_patent: form.has_patent,
        is_female_ent: form.is_female_ent,
        is_ventured: form.is_ventured,
      },
    });
    setResult(res);
  };

  const reset = () => {
    setResult(null);
    executeMut.reset();
    setPrefilled(false);
  };

  if (prepareQ.isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-5 pb-10">
      <header className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link href="/dashboard">
            <ArrowLeft className="h-4 w-4" />
            대시보드
          </Link>
        </Button>
      </header>

      <div className="space-y-1">
        <h1>정밀진단</h1>
        <p className="text-sm text-ink-secondary">
          현재 사업 상태를 기반으로 정책자금 심사 적합도를 점수로 확인하세요.
        </p>
      </div>

      {!result ? (
        /* ── 입력 폼 ── */
        <form onSubmit={handleSubmit} className="space-y-4">
          {prepareQ.data?.missing_fields && prepareQ.data.missing_fields.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              누락된 정보가 있어요: <strong>{prepareQ.data.missing_fields.join(", ")}</strong>
              <br />
              <span className="text-xs">아래 폼에서 직접 입력해주세요.</span>
            </div>
          )}

          {/* ── 재무 정보 ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">재무 정보</CardTitle>
              <CardDescription>금액은 원(₩) 단위, 콤마 자동 입력됩니다.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-ink">연매출 (원)</label>
                  <div className="relative">
                    <input
                      type="text"
                      inputMode="numeric"
                      placeholder="예: 300,000,000"
                      value={form.annual_revenue}
                      onChange={(e) =>
                        setForm((p) => ({
                          ...p,
                          annual_revenue: formatComma(e.target.value),
                        }))
                      }
                      className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-tertiary">원</span>
                  </div>
                  {form.annual_revenue && (
                    <p className="text-xs text-ink-tertiary">
                      {parseComma(form.annual_revenue)?.toLocaleString("ko-KR")}원
                    </p>
                  )}
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-ink">총부채 (원)</label>
                  <div className="relative">
                    <input
                      type="text"
                      inputMode="numeric"
                      placeholder="예: 100,000,000"
                      value={form.total_debt}
                      onChange={(e) =>
                        setForm((p) => ({
                          ...p,
                          total_debt: formatComma(e.target.value),
                        }))
                      }
                      className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-tertiary">원</span>
                  </div>
                  {form.total_debt && form.annual_revenue && parseComma(form.annual_revenue)! > 0 && (
                    <p className="text-xs text-ink-tertiary">
                      부채비율 약{" "}
                      {Math.round(
                        (parseComma(form.total_debt)! / parseComma(form.annual_revenue)!) * 100
                      )}
                      %
                    </p>
                  )}
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-ink">상시 근로자 수 (명)</label>
                <input
                  type="number"
                  min="0"
                  required
                  placeholder="예: 5"
                  value={form.employee_count}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, employee_count: e.target.value }))
                  }
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>

              {/* 자금 용도 */}
              <div className="space-y-1">
                <label className="text-sm font-medium text-ink">
                  자금 용도 <span className="text-xs font-normal text-ink-tertiary">(선택)</span>
                </label>
                <div className="relative">
                  <select
                    value={form.funding_purpose}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, funding_purpose: e.target.value }))
                    }
                    className="w-full appearance-none rounded-lg border border-surface-border bg-surface px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                  >
                    {FUNDING_PURPOSE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-tertiary" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ── 세금 체납 ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">세금·공과금 체납 여부</CardTitle>
              <CardDescription>체납 중인 항목이 있으면 자동으로 🔴 빨간불 처리됩니다.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* 체납 여부 토글 */}
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition-colors",
                  form.has_tax_arrears
                    ? "border-red-300 bg-red-50"
                    : "border-surface-border hover:bg-surface-subtle"
                )}
              >
                <input
                  type="checkbox"
                  className="accent-red-600 h-4 w-4"
                  checked={form.has_tax_arrears}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, has_tax_arrears: e.target.checked }))
                  }
                />
                <div>
                  <p className={cn("text-sm font-medium", form.has_tax_arrears ? "text-red-700" : "text-ink")}>
                    현재 체납 중인 항목이 있습니다
                  </p>
                  <p className="text-xs text-ink-tertiary">체크 시 해당 항목을 상세 선택해주세요</p>
                </div>
              </label>

              {/* 체납 상세 — 체크 시 펼침 */}
              {form.has_tax_arrears && (
                <div className="rounded-lg border border-red-200 bg-red-50/50 p-4 space-y-3">
                  <p className="text-xs font-semibold text-red-700">체납 항목 선택 (해당되는 것 모두 선택)</p>
                  <div className="space-y-2">
                    {TAX_TYPE_OPTIONS.map(({ key, label }) => (
                      <label key={key} className="flex cursor-pointer items-center gap-2 text-sm text-red-700">
                        <input
                          type="checkbox"
                          className="accent-red-600"
                          checked={form.tax_types[key as keyof typeof form.tax_types]}
                          onChange={(e) =>
                            setForm((p) => ({
                              ...p,
                              tax_types: { ...p.tax_types, [key]: e.target.checked },
                            }))
                          }
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-red-700">체납 총액 (원, 대략)</label>
                    <div className="relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        placeholder="예: 5,000,000"
                        value={form.tax_amount}
                        onChange={(e) =>
                          setForm((p) => ({ ...p, tax_amount: formatComma(e.target.value) }))
                        }
                        className="w-full rounded-lg border border-red-200 bg-white px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-tertiary">원</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ── 가점 항목 ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">가점 항목</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {(
                  [
                    { key: "has_patent", label: "특허 보유", desc: "+5점" },
                    { key: "is_female_ent", label: "여성기업", desc: "+3점" },
                    { key: "is_ventured", label: "벤처 인증", desc: "+7점" },
                  ] as const
                ).map(({ key, label, desc }) => (
                  <label
                    key={key}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 transition-colors",
                      form[key]
                        ? "border-primary-300 bg-primary-50 text-primary-700"
                        : "border-surface-border hover:bg-surface-subtle"
                    )}
                  >
                    <input
                      type="checkbox"
                      className="accent-primary-600"
                      checked={form[key]}
                      onChange={(e) =>
                        setForm((p) => ({ ...p, [key]: e.target.checked }))
                      }
                    />
                    <span className="text-sm font-medium">{label}</span>
                    <span className="ml-auto text-xs text-ink-tertiary">{desc}</span>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={executeMut.isPending}
          >
            {executeMut.isPending ? (
              <>
                <Loader2 className="animate-spin" />
                진단 중...
              </>
            ) : (
              "정밀진단 실행"
            )}
          </Button>

          {executeMut.isError && (
            <p className="text-center text-sm text-red-600">
              진단 중 오류가 발생했습니다. 다시 시도해주세요.
            </p>
          )}
        </form>
      ) : (
        /* ── 결과 표시 ── */
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col items-center gap-5 sm:flex-row sm:gap-8">
                <ScoreGauge score={Math.round(result.total_score)} size="lg" label="진단 점수" />
                <div className="flex-1 space-y-3 text-center sm:text-left">
                  <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                    <TrafficLightBadge
                      status={result.traffic_light.toLowerCase() as "green" | "yellow" | "red"}
                    />
                    <span
                      className={`rounded-full px-3 py-0.5 text-sm font-semibold ${GRADE_COLOR[result.grade] ?? "bg-surface-subtle text-ink"}`}
                    >
                      {GRADE_LABEL[result.grade] ?? result.grade}
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-ink">
                    {Math.round(result.total_score)}점
                  </p>
                  {detailQ.isLoading ? (
                    <p className="text-sm text-ink-tertiary">AI 코멘트 로딩 중...</p>
                  ) : detailQ.data?.ai_comment ? (
                    <p className="text-sm text-ink-secondary leading-relaxed">
                      {detailQ.data.ai_comment}
                    </p>
                  ) : null}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
            <p className="text-xs text-ink-tertiary">
              이 결과는 규칙 기반 참고 점수입니다. 실제 심사 결과와 다를 수 있어요.
            </p>
          </div>

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={reset}>
              다시 진단하기
            </Button>
            <Button asChild variant="primary" className="flex-1">
              <Link href={"/policies/matching" as never}>정밀 추천 결과 보기</Link>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
