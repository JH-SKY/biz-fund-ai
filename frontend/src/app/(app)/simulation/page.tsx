"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  Minus,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMyBusiness } from "@/hooks/useDashboard";
import {
  useExecuteSimulation,
  useMyFinanceSnapshot,
} from "@/hooks/useDiagnosis";
import type { ExecuteSimulationResponse } from "@/types";

function formatWon(value: number | null | undefined): string {
  if (value == null) return "미입력";
  return `${value.toLocaleString("ko-KR")}원`;
}

export default function SimulationPage() {
  const businessQ = useMyBusiness();
  const financeQ = useMyFinanceSnapshot();
  const simulateMut = useExecuteSimulation();

  const business = businessQ.data;
  const finance = financeQ.data;

  const [form, setForm] = useState({
    annual_revenue: "",
    total_debt: "",
    employee_count: "",
    has_patent: false,
    is_female_ent: false,
    is_ventured: false,
    has_tax_arrears: false,
  });
  const [result, setResult] = useState<ExecuteSimulationResponse | null>(null);

  useEffect(() => {
    if (!business && !finance) return;
    setForm({
      annual_revenue:
        finance?.annual_revenue != null ? String(finance.annual_revenue) : "",
      total_debt: finance?.total_debt != null ? String(finance.total_debt) : "",
      employee_count:
        finance?.employee_count != null
          ? String(finance.employee_count)
          : business?.employee_count != null
            ? String(business.employee_count)
            : "",
      has_patent: business?.has_patent ?? false,
      is_female_ent: business?.is_female_ent ?? false,
      is_ventured: business?.is_ventured ?? false,
      has_tax_arrears: business?.has_tax_arrears ?? false,
    });
  }, [business, finance]);

  const debtRatio = useMemo(() => {
    const revenue = Number(form.annual_revenue);
    const debt = Number(form.total_debt);
    if (!revenue || !debt || revenue <= 0) return null;
    return Math.round((debt / revenue) * 100);
  }, [form.annual_revenue, form.total_debt]);

  const handleSimulate = async (event: React.FormEvent) => {
    event.preventDefault();
    const response = await simulateMut.mutateAsync({
      virtual_conditions: {
        annual_revenue: form.annual_revenue ? Number(form.annual_revenue) : null,
        total_debt: form.total_debt ? Number(form.total_debt) : null,
        employee_count: Number(form.employee_count) || 0,
        has_patent: form.has_patent,
        is_female_ent: form.is_female_ent,
        is_ventured: form.is_ventured,
        has_tax_arrears: form.has_tax_arrears,
      },
    });
    setResult(response);
  };

  const diff = result ? Math.round(result.simulated_rate - result.base_rate) : 0;

  if (businessQ.isLoading || financeQ.isLoading) {
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

      <div className="space-y-1">
        <h1>진단 시뮬레이션</h1>
        <p className="text-sm text-ink-secondary">
          사업장 조건을 바꾸면 정밀진단 점수가 어떻게 달라지는지 미리
          확인해 보세요. 정책별 가점 시뮬레이션이 아니라 내 사업장 체력의
          변화량을 보는 기능입니다.
        </p>
      </div>

      <form onSubmit={handleSimulate} className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">가정할 변화</CardTitle>
            <CardDescription>
              현재 저장된 값을 불러왔습니다. 바꾸고 싶은 항목만 수정하세요.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-sm font-medium text-ink">
                연 매출
                {finance?.annual_revenue != null ? (
                  <span className="ml-1 text-xs font-normal text-ink-tertiary">
                    현재 {formatWon(finance.annual_revenue)}
                  </span>
                ) : null}
              </label>
              <input
                type="number"
                min="0"
                placeholder="연 매출 입력"
                value={form.annual_revenue}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    annual_revenue: event.target.value,
                  }))
                }
                className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-ink">
                총 부채
                {finance?.total_debt != null ? (
                  <span className="ml-1 text-xs font-normal text-ink-tertiary">
                    현재 {formatWon(finance.total_debt)}
                  </span>
                ) : null}
              </label>
              <input
                type="number"
                min="0"
                placeholder="총 부채 입력"
                value={form.total_debt}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    total_debt: event.target.value,
                  }))
                }
                className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
              {debtRatio != null ? (
                <p className="text-xs text-ink-tertiary">
                  예상 부채비율 {debtRatio}%
                </p>
              ) : null}
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-ink">
                상시 근로자 수
                {business?.employee_count != null ? (
                  <span className="ml-1 text-xs font-normal text-ink-tertiary">
                    현재 {business.employee_count}명
                  </span>
                ) : null}
              </label>
              <input
                type="number"
                min="0"
                placeholder="직원 수 입력"
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
            <CardTitle className="text-base">상태 변화</CardTitle>
            <CardDescription>
              기술성 강화나 체납 해소 같은 변화도 함께 가정할 수 있습니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-4">
              {(
                [
                  { key: "has_tax_arrears", label: "체납 있음", danger: true },
                  { key: "has_patent", label: "특허 보유", danger: false },
                  { key: "is_female_ent", label: "여성기업", danger: false },
                  { key: "is_ventured", label: "벤처 인증", danger: false },
                ] as const
              ).map(({ key, label, danger }) => (
                <label
                  key={key}
                  className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                    form[key]
                      ? danger
                        ? "border-red-300 bg-red-50 text-red-700"
                        : "border-primary-300 bg-primary-50 text-primary-700"
                      : "border-surface-border hover:bg-surface-subtle"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={form[key]}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        [key]: event.target.checked,
                      }))
                    }
                    className="accent-primary-600"
                  />
                  {label}
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
          disabled={simulateMut.isPending}
        >
          {simulateMut.isPending ? (
            <>
              <Loader2 className="animate-spin" />
              시뮬레이션 계산 중...
            </>
          ) : (
            "시뮬레이션 실행"
          )}
        </Button>
      </form>

      {result ? (
        <div className="space-y-4">
          <Card className="overflow-hidden">
            <CardHeader className="bg-surface-subtle pb-3">
              <CardTitle className="text-base">진단 점수 비교</CardTitle>
            </CardHeader>
            <CardContent className="pt-5">
              <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-around">
                <div className="text-center">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-tertiary">
                    현재 점수
                  </p>
                  <ScoreGauge score={Math.round(result.base_rate)} size="md" />
                </div>

                <div className="flex flex-col items-center gap-1">
                  {diff > 0 ? (
                    <TrendingUp className="h-8 w-8 text-green-600" />
                  ) : diff < 0 ? (
                    <TrendingDown className="h-8 w-8 text-red-500" />
                  ) : (
                    <Minus className="h-8 w-8 text-ink-tertiary" />
                  )}
                  <span
                    className={`text-xl font-bold ${
                      diff > 0
                        ? "text-green-600"
                        : diff < 0
                          ? "text-red-500"
                          : "text-ink-tertiary"
                    }`}
                  >
                    {diff > 0 ? `+${diff}` : diff}점
                  </span>
                </div>

                <div className="text-center">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-primary-700">
                    변화 후 점수
                  </p>
                  <ScoreGauge
                    score={Math.round(result.simulated_rate)}
                    size="md"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">무엇이 바뀌었나</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5">
                {result.gain_factors.map((factor, index) => (
                  <li
                    key={`${factor}-${index}`}
                    className="text-sm text-ink-secondary"
                  >
                    • {factor}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => {
                setResult(null);
                simulateMut.reset();
              }}
            >
              다시 시뮬레이션
            </Button>
            <Button asChild variant="primary" className="flex-1">
              <Link href={"/diagnosis" as never}>정밀진단으로 돌아가기</Link>
            </Button>
          </div>
        </div>
      ) : null}

      {simulateMut.isError ? (
        <p className="text-center text-sm text-red-600">
          시뮬레이션 중 오류가 발생했습니다. 다시 시도해 주세요.
        </p>
      ) : null}
    </div>
  );
}
