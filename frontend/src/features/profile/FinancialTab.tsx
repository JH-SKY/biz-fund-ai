"use client";

/**
 * 재무 현황 탭 — 연도별 매출/직원수/부채비율 테이블 + 재무 추가/삭제.
 */

import * as React from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  useFinanceList,
  useCreateFinance,
  useDeleteFinance,
} from "@/hooks/useProfile";
import type { FinanceCreateRequest } from "@/types";

const PERIOD_OPTIONS = [
  { value: "ANNUAL", label: "연간" },
  { value: "1Q", label: "1분기" },
  { value: "2Q", label: "2분기" },
  { value: "3Q", label: "3분기" },
  { value: "4Q", label: "4분기" },
];

function formatKRW(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(1)}억`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(0)}만`;
  return value.toLocaleString();
}

function formatCount(value: number | null | undefined, unit: string): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value}${unit}` : "-";
}

function formatPercent(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toFixed(1)}%`
    : "-";
}

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 6 }, (_, i) => {
  const y = CURRENT_YEAR - i;
  return { value: String(y), label: `${y}년` };
});

const EMPTY_FORM: FinanceCreateRequest = {
  snapshot_year: CURRENT_YEAR,
  snapshot_period: "ANNUAL",
  annual_revenue: null,
  operating_profit: null,
  net_income: null,
  total_debt: null,
  capital: null,
  employee_count: null,
  tax_arrears_yn: false,
};

export function FinancialTab() {
  const { data: finances, isLoading } = useFinanceList();
  const createFinance = useCreateFinance();
  const deleteFinance = useDeleteFinance();

  const [open, setOpen] = React.useState(false);
  const [form, setForm] = React.useState<FinanceCreateRequest>(EMPTY_FORM);

  function patchForm<K extends keyof FinanceCreateRequest>(
    key: K,
    value: FinanceCreateRequest[K]
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleCreate() {
    await createFinance.mutateAsync(form);
    setOpen(false);
    setForm(EMPTY_FORM);
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-surface-subtle" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-secondary">
          연도·분기별 재무 데이터를 입력하면 정책 매칭 정확도가 올라갑니다.
        </p>
        <Button size="sm" onClick={() => setOpen(true)} className="gap-1.5">
          <Plus className="h-4 w-4" />
          재무 추가
        </Button>
      </div>

      {!finances || finances.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <p className="text-3xl">📊</p>
            <p className="text-sm font-semibold text-ink">
              등록된 재무 정보가 없습니다
            </p>
            <p className="text-xs text-ink-secondary">
              재무 데이터를 추가하면 AI 진단 정확도가 향상됩니다.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-surface-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-surface-subtle text-left text-xs font-semibold text-ink-secondary">
                <th className="px-4 py-3">연도</th>
                <th className="px-4 py-3">기간</th>
                <th className="px-4 py-3 text-right">매출액</th>
                <th className="px-4 py-3 text-right">영업이익</th>
                <th className="px-4 py-3 text-right">직원수</th>
                <th className="px-4 py-3 text-right">부채비율</th>
                <th className="px-4 py-3 text-center">검증</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {finances.map((f) => (
                <tr
                  key={f.finance_id ?? `${f.snapshot_year}-${f.snapshot_period}`}
                  className="border-b border-surface-border last:border-0 hover:bg-surface-subtle/50"
                >
                  <td className="px-4 py-3 font-medium numeric">
                    {f.snapshot_year}
                  </td>
                  <td className="px-4 py-3 text-ink-secondary">
                    {f.snapshot_period}
                  </td>
                  <td className="px-4 py-3 text-right numeric">
                    {formatKRW(f.annual_revenue)}
                  </td>
                  <td className="px-4 py-3 text-right numeric">
                    {formatKRW(f.operating_profit)}
                  </td>
                  <td className="px-4 py-3 text-right numeric">
                    {formatCount(f.employee_count, "명")}
                  </td>
                  <td className="px-4 py-3 text-right numeric">
                    {formatPercent(f.debt_ratio)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge
                      variant={f.is_verified ? "success" : "default"}
                      size="sm"
                    >
                      {f.is_verified ? "검증" : "미검증"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => deleteFinance.mutate(f.snapshot_year)}
                      aria-label="재무 삭제"
                      className="rounded p-1.5 text-ink-tertiary transition-colors hover:bg-danger-50 hover:text-danger-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="재무 정보 추가"
        description="연도·분기를 선택하고 금액을 입력하세요. (단위: 원)"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              취소
            </Button>
            <Button
              onClick={handleCreate}
              loading={createFinance.isPending}
            >
              추가
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>연도</Label>
              <Select
                options={YEAR_OPTIONS}
                value={String(form.snapshot_year)}
                onChange={(e) =>
                  patchForm("snapshot_year", Number(e.target.value))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>기간</Label>
              <Select
                options={PERIOD_OPTIONS}
                value={form.snapshot_period ?? "ANNUAL"}
                onChange={(e) =>
                  patchForm(
                    "snapshot_period",
                    e.target.value as FinanceCreateRequest["snapshot_period"]
                  )
                }
              />
            </div>
          </div>

          {(
            [
              { key: "annual_revenue", label: "매출액" },
              { key: "operating_profit", label: "영업이익" },
              { key: "net_income", label: "당기순이익" },
              { key: "total_debt", label: "총부채" },
              { key: "capital", label: "자본금" },
            ] as const
          ).map(({ key, label }) => (
            <div key={key} className="space-y-1.5">
              <Label>{label} (원)</Label>
              <Input
                type="number"
                placeholder="0"
                value={form[key] ?? ""}
                onChange={(e) =>
                  patchForm(
                    key,
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
          ))}

          <div className="space-y-1.5">
            <Label>직원수 (명)</Label>
            <Input
              type="number"
              placeholder="0"
              value={form.employee_count ?? ""}
              onChange={(e) =>
                patchForm(
                  "employee_count",
                  e.target.value === "" ? null : Number(e.target.value)
                )
              }
            />
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.tax_arrears_yn ?? false}
              onChange={(e) => patchForm("tax_arrears_yn", e.target.checked)}
              className="h-4 w-4 rounded border-surface-border accent-primary-600"
            />
            세금 체납 여부
          </label>
        </div>
      </Dialog>
    </div>
  );
}
