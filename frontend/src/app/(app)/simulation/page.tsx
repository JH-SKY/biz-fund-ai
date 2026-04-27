"use client";

/**
 * [PAGE] 시뮬레이션 — /simulation
 *
 * 흐름:
 *   1. useMyBusiness + useMyFinanceSnapshot → 현재값 사전 채움
 *   2. 사용자가 조건 변경 (연매출, 총부채, 직원수, 특허/벤처/여성기업 toggle)
 *   3. POST /simulations (policy_id 없음) → base_rate vs simulated_rate 비교 표시
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, TrendingUp, TrendingDown, Minus } from "lucide-react";

import { ScoreGauge } from "@/components/shared/ScoreGauge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { useMyBusiness } from "@/hooks/useDashboard";
import {
  useExecuteSimulation,
  useMyFinanceSnapshot,
} from "@/hooks/useDiagnosis";
import type { ExecuteSimulationResponse } from "@/types";

function formatWon(v: number | null | undefined): string {
  if (v == null) return "미입력";
  if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}억원`;
  if (v >= 10_000) return `${Math.round(v / 10_000).toLocaleString()}만원`;
  return `${v.toLocaleString()}원`;
}

export default function SimulationPage() {
  const bizQ = useMyBusiness();
  const finQ = useMyFinanceSnapshot();
  const simMut = useExecuteSimulation();

  const biz = bizQ.data;
  const fin = finQ.data;

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

  // 사전 채움
  useEffect(() => {
    if (!biz && !fin) return;
    setForm({
      annual_revenue: fin?.annual_revenue != null ? String(fin.annual_revenue) : "",
      total_debt: fin?.total_debt != null ? String(fin.total_debt) : "",
      employee_count:
        fin?.employee_count != null
          ? String(fin.employee_count)
          : biz?.employee_count != null
            ? String(biz.employee_count)
            : "",
      has_patent: biz?.has_patent ?? false,
      is_female_ent: biz?.is_female_ent ?? false,
      is_ventured: biz?.is_ventured ?? false,
      has_tax_arrears: biz?.has_tax_arrears ?? false,
    });
  }, [biz, fin]);

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await simMut.mutateAsync({
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
    setResult(res);
  };

  const diff = result ? Math.round(result.simulated_rate - result.base_rate) : 0;

  if (bizQ.isLoading || finQ.isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5 pb-10">
      <header className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link href="/dashboard">
            <ArrowLeft className="h-4 w-4" />
            대시보드
          </Link>
        </Button>
      </header>

      <div className="space-y-1">
        <h1>시뮬레이션</h1>
        <p className="text-sm text-ink-secondary">
          조건을 바꾸면 점수가 어떻게 달라지는지 확인해보세요.
          <br />
          <span className="text-xs text-ink-tertiary">
            현재값이 사전 채워져 있습니다. 변경하고 싶은 항목만 수정하세요.
          </span>
        </p>
      </div>

      <form onSubmit={handleSimulate} className="space-y-4">
        {/* ── 수치 입력 ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">수치 조건 변경</CardTitle>
            <CardDescription>빈 칸은 0으로 처리됩니다.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-sm font-medium text-ink">
                  연매출 (원)
                  {fin?.annual_revenue != null && (
                    <span className="ml-1 text-xs font-normal text-ink-tertiary">
                      현재 {formatWon(fin.annual_revenue)}
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  min="0"
                  placeholder="연매출 입력"
                  value={form.annual_revenue}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, annual_revenue: e.target.value }))
                  }
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-ink">
                  총부채 (원)
                  {fin?.total_debt != null && (
                    <span className="ml-1 text-xs font-normal text-ink-tertiary">
                      현재 {formatWon(fin.total_debt)}
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  min="0"
                  placeholder="총부채 입력"
                  value={form.total_debt}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, total_debt: e.target.value }))
                  }
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-ink">
                  상시 근로자 (명)
                  {biz?.employee_count != null && (
                    <span className="ml-1 text-xs font-normal text-ink-tertiary">
                      현재 {biz.employee_count}명
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  min="0"
                  placeholder="직원 수"
                  value={form.employee_count}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, employee_count: e.target.value }))
                  }
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ── 가점 항목 toggle ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">가점 항목</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {(
                [
                  { key: "has_tax_arrears", label: "세금 체납", warn: true as boolean },
                  { key: "has_patent", label: "특허 보유", warn: false as boolean },
                  { key: "is_female_ent", label: "여성기업", warn: false as boolean },
                  { key: "is_ventured", label: "벤처 인증", warn: false as boolean },
                ] as const
              ).map(({ key, label, warn }) => (
                <label
                  key={key}
                  className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                    form[key]
                      ? warn
                        ? "border-red-300 bg-red-50 text-red-700"
                        : "border-primary-300 bg-primary-50 text-primary-700"
                      : "border-surface-border hover:bg-surface-subtle"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="accent-primary-600"
                    checked={form[key]}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, [key]: e.target.checked }))
                    }
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
          disabled={simMut.isPending}
        >
          {simMut.isPending ? (
            <>
              <Loader2 className="animate-spin" />
              시뮬레이션 계산 중...
            </>
          ) : (
            "시뮬레이션 실행"
          )}
        </Button>
      </form>

      {/* ── 결과 ── */}
      {result && (
        <div className="space-y-4">
          <Card className="overflow-hidden">
            <CardHeader className="bg-surface-subtle pb-3">
              <CardTitle className="text-base">점수 비교</CardTitle>
            </CardHeader>
            <CardContent className="pt-5">
              <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-around">
                <div className="text-center">
                  <p className="mb-2 text-xs font-semibold text-ink-tertiary uppercase tracking-wider">
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
                  <p className="mb-2 text-xs font-semibold text-primary-700 uppercase tracking-wider">
                    시뮬 점수
                  </p>
                  <ScoreGauge score={Math.round(result.simulated_rate)} size="md" />
                </div>
              </div>
            </CardContent>
          </Card>

          {result.gain_factors.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">변경 내역</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5">
                  {result.gain_factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-ink-secondary">
                      <span className="mt-0.5 text-primary-500">·</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => {
                setResult(null);
                simMut.reset();
              }}
            >
              다시 시뮬레이션
            </Button>
            <Button asChild variant="primary" className="flex-1">
              <Link href={"/diagnosis" as never}>정밀진단 받기</Link>
            </Button>
          </div>
        </div>
      )}

      {simMut.isError && (
        <p className="text-center text-sm text-red-600">
          시뮬레이션 중 오류가 발생했습니다. 다시 시도해주세요.
        </p>
      )}
    </div>
  );
}
