"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { TrafficLightBadge } from "@/components/shared/TrafficLightBadge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useDiagnosisDetail,
  useExecuteDiagnosis,
  usePrepareDiagnosis,
} from "@/hooks/useDiagnosis";
import { cn } from "@/lib/utils";
import type { ExecuteDiagnosisResponse } from "@/types";

const GRADE_LABEL: Record<string, string> = {
  EXCELLENT: "우수",
  GOOD: "양호",
  NORMAL: "보통",
  RISK: "주의",
};

const GRADE_COLOR: Record<string, string> = {
  EXCELLENT: "bg-green-100 text-green-800",
  GOOD: "bg-blue-100 text-blue-800",
  NORMAL: "bg-yellow-100 text-yellow-800",
  RISK: "bg-red-100 text-red-800",
};

const AXIS_META = [
  {
    key: "financial_health",
    label: "재무건전성",
    description: "매출 규모와 부채 부담을 중심으로 봅니다.",
  },
  {
    key: "growth_potential",
    label: "성장성",
    description: "매출 확장 여지와 기술·혁신 신호를 봅니다.",
  },
  {
    key: "operational_stability",
    label: "운영안정성",
    description: "인력 기반과 업력, 운영 지속 가능성을 봅니다.",
  },
  {
    key: "risk_management",
    label: "리스크관리",
    description: "체납과 과도한 부채 같은 위험 신호를 봅니다.",
  },
] as const;

function formatComma(value: string): string {
  const digits = value.replace(/[^0-9]/g, "");
  if (!digits) return "";
  return Number(digits).toLocaleString("ko-KR");
}

function parseComma(value: string): number | null {
  const digits = value.replace(/[^0-9]/g, "");
  return digits ? Number(digits) : null;
}

export default function DiagnosisPage() {
  const prepareQ = usePrepareDiagnosis();
  const executeMut = useExecuteDiagnosis();

  const [result, setResult] = useState<ExecuteDiagnosisResponse | null>(null);
  const [form, setForm] = useState({
    annual_revenue: "",
    total_debt: "",
    employee_count: "",
    has_tax_arrears: false,
    has_patent: false,
    is_female_ent: false,
    is_ventured: false,
  });

  const detailQ = useDiagnosisDetail(result?.diagnosis_id ?? null);
  const snapshot = prepareQ.data?.current_snapshot;

  useEffect(() => {
    if (!snapshot || result) return;
    setForm((prev) => ({
      ...prev,
      annual_revenue:
        snapshot.revenue != null
          ? Number(snapshot.revenue).toLocaleString("ko-KR")
          : prev.annual_revenue,
      total_debt:
        snapshot.total_debt != null
          ? Number(snapshot.total_debt).toLocaleString("ko-KR")
          : prev.total_debt,
      employee_count:
        snapshot.employee_count != null
          ? String(snapshot.employee_count)
          : prev.employee_count,
    }));
  }, [snapshot, result]);

  const debtRatio = useMemo(() => {
    const revenue = parseComma(form.annual_revenue);
    const debt = parseComma(form.total_debt);
    if (!revenue || !debt || revenue <= 0) return null;
    return Math.round((debt / revenue) * 100);
  }, [form.annual_revenue, form.total_debt]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const response = await executeMut.mutateAsync({
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
    setResult(response);
  };

  const reset = () => {
    setResult(null);
    executeMut.reset();
  };

  if (prepareQ.isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 pb-10">
      <header className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link href="/dashboard">
            <ArrowLeft className="h-4 w-4" />
            대시보드
          </Link>
        </Button>
      </header>

      <div className="space-y-2">
        <h1>정밀진단</h1>
        <p className="text-sm text-ink-secondary">
          정책 추천이 아니라 내 사업장 자체의 건강 상태를 진단합니다.
          매출, 부채, 인력, 체납 여부를 바탕으로 지금 가장 먼저 손봐야 할
          리스크를 확인하세요.
        </p>
      </div>

      {!result ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          <Card className="border-primary-200 bg-primary-50/60">
            <CardContent className="flex gap-3 pt-6 text-sm text-primary-900">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
              <div className="space-y-1">
                <p className="font-semibold">이번 진단에서 보는 것</p>
                <p>
                  재무건전성, 성장성, 운영안정성, 리스크관리 4축으로 사업장
                  컨디션을 평가합니다. 진단 후에는 이 정보를 바탕으로 맞춤정책
                  추천 정확도도 함께 올라갑니다.
                </p>
              </div>
            </CardContent>
          </Card>

          {prepareQ.data?.missing_fields.length ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              현재 저장된 정보만으로는{" "}
              <strong>{prepareQ.data.missing_fields.join(", ")}</strong> 값이
              비어 있습니다. 아래에서 직접 입력하면 더 정확하게 진단할 수
              있습니다.
            </div>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">핵심 재무 정보</CardTitle>
              <CardDescription>
                숫자는 원 단위로 입력하면 자동으로 쉼표가 들어갑니다.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm font-medium text-ink">연 매출</label>
                <div className="relative">
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="예: 300,000,000"
                    value={form.annual_revenue}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        annual_revenue: formatComma(event.target.value),
                      }))
                    }
                    className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-tertiary">
                    원
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-ink">총 부채</label>
                <div className="relative">
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="예: 100,000,000"
                    value={form.total_debt}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        total_debt: formatComma(event.target.value),
                      }))
                    }
                    className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-tertiary">
                    원
                  </span>
                </div>
                {debtRatio != null ? (
                  <p className="text-xs text-ink-tertiary">
                    예상 부채비율 {debtRatio}%
                  </p>
                ) : null}
              </div>

              <div className="space-y-1 sm:col-span-2">
                <label className="text-sm font-medium text-ink">
                  상시 근로자 수
                </label>
                <input
                  type="number"
                  min="0"
                  required
                  placeholder="예: 5"
                  value={form.employee_count}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      employee_count: event.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">리스크 신호</CardTitle>
              <CardDescription>
                체납은 사업장 건전성에 가장 큰 악영향을 주는 항목입니다.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <label
                className={cn(
                  "flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 transition-colors",
                  form.has_tax_arrears
                    ? "border-red-300 bg-red-50"
                    : "border-surface-border hover:bg-surface-subtle"
                )}
              >
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 accent-red-600"
                  checked={form.has_tax_arrears}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      has_tax_arrears: event.target.checked,
                    }))
                  }
                />
                <div className="space-y-1">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      form.has_tax_arrears ? "text-red-700" : "text-ink"
                    )}
                  >
                    현재 체납 중인 세금 또는 4대 보험료가 있습니다
                  </p>
                  <p className="text-xs text-ink-tertiary">
                    체크하면 리스크관리 점수가 크게 낮아지고 전체 진단도
                    보수적으로 계산됩니다.
                  </p>
                </div>
              </label>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">성장 신호</CardTitle>
              <CardDescription>
                기술성과 혁신성은 성장성 평가에 반영됩니다.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-3">
                {(
                  [
                    { key: "has_patent", label: "특허 보유" },
                    { key: "is_female_ent", label: "여성기업" },
                    { key: "is_ventured", label: "벤처 인증" },
                  ] as const
                ).map(({ key, label }) => (
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
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          [key]: event.target.checked,
                        }))
                      }
                    />
                    <span className="text-sm font-medium">{label}</span>
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
                정밀진단 실행 중...
              </>
            ) : (
              "정밀진단 실행"
            )}
          </Button>

          {executeMut.isError ? (
            <p className="text-center text-sm text-red-600">
              진단 중 오류가 발생했습니다. 다시 시도해 주세요.
            </p>
          ) : null}
        </form>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col items-center gap-5 sm:flex-row sm:gap-8">
                <ScoreGauge
                  score={Math.round(result.total_score)}
                  size="lg"
                  label="종합 진단"
                />
                <div className="flex-1 space-y-3 text-center sm:text-left">
                  <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                    <TrafficLightBadge
                      status={result.traffic_light.toLowerCase() as "green" | "yellow" | "red"}
                      label={
                        result.traffic_light === "GREEN"
                          ? "안정 구간"
                          : result.traffic_light === "YELLOW"
                            ? "주의 구간"
                            : "위험 구간"
                      }
                    />
                    <span
                      className={`rounded-full px-3 py-0.5 text-sm font-semibold ${
                        GRADE_COLOR[result.grade] ?? "bg-surface-subtle text-ink"
                      }`}
                    >
                      {GRADE_LABEL[result.grade] ?? result.grade}
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-ink">
                    {Math.round(result.total_score)}점
                  </p>
                  {detailQ.isLoading ? (
                    <p className="text-sm text-ink-tertiary">
                      세부 진단 근거를 불러오는 중입니다...
                    </p>
                  ) : (
                    <p className="text-sm leading-relaxed text-ink-secondary">
                      {detailQ.data?.summary}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {detailQ.data ? (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                {AXIS_META.map((axis) => (
                  <Card key={axis.key}>
                    <CardContent className="space-y-2 pt-5">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-ink">
                            {axis.label}
                          </p>
                          <p className="text-xs text-ink-tertiary">
                            {axis.description}
                          </p>
                        </div>
                        <span className="text-lg font-bold text-ink">
                          {Math.round(detailQ.data.scores[axis.key])}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      현재 강점
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm text-ink-secondary">
                      {detailQ.data.strengths.map((item, index) => (
                        <li key={`${item}-${index}`}>• {item}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      위험 신호
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm text-ink-secondary">
                      {detailQ.data.risk_signals.map((item, index) => (
                        <li key={`${item}-${index}`}>• {item}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <TrendingUp className="h-4 w-4 text-primary-600" />
                      바로 할 일
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm text-ink-secondary">
                      {detailQ.data.action_items.map((item, index) => (
                        <li key={`${item}-${index}`}>• {item}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : null}

          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
            <p className="text-xs text-ink-tertiary">
              진단 결과는 사업장 건강 상태를 보기 위한 기준점입니다. 이
              정보를 바탕으로 맞춤정책 추천은 더 보수적이고 정확하게 다시
              계산됩니다.
            </p>
          </div>

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={reset}>
              다시 진단하기
            </Button>
            <Button asChild variant="primary" className="flex-1">
              <Link href={"/policies/matching" as never}>
                정밀 추천 결과 보기
              </Link>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
