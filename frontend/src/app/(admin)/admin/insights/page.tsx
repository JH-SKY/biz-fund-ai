"use client";

/**
 * /admin/insights — 비즈니스 전략 대시보드.
 *
 * 기능 (PAGE 12 ④)
 *  - 미충족 수요 분석: 매칭 결과 0건이었던 사용자 질의 키워드 랭킹
 *  - 수익 전환 통계: 전문가 상담 예약 · 솔루션 클릭/전환
 */

import * as React from "react";
import {
  Calendar,
  MessagesSquare,
  Search,
  ShoppingBag,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminPagination,
  AdminTableSkeleton,
  StatCard,
} from "@/features/admin";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useConversionStats, useUnmetDemand } from "@/hooks/useAdmin";
import type { ApiError } from "@/types";

export default function AdminInsightsPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <InsightsContent />
      </AdminShell>
    </AdminGuard>
  );
}

function InsightsContent() {
  // 미충족 수요
  const [page, setPage] = React.useState(1);
  const demand = useUnmetDemand(page, 20);

  // 수익 전환 기간 필터
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
  const [from, setFrom] = React.useState(firstDay.toISOString().slice(0, 10));
  const [to, setTo] = React.useState(today.toISOString().slice(0, 10));
  const conversion = useConversionStats(from, to);

  const demandItems = demand.data?.items ?? [];
  const demandTotal = demand.data?.total_count ?? 0;
  const demandPages = demand.data?.total_pages ?? 1;

  const conv = conversion.data;
  const solutionChart =
    conv?.solution_clicks.map((s) => ({
      name: s.solution_label,
      클릭: s.clicks,
      전환: s.conversions,
    })) ?? [];

  const totalClicks =
    conv?.solution_clicks.reduce((sum, s) => sum + s.clicks, 0) ?? 0;
  const totalConversions =
    conv?.solution_clicks.reduce((sum, s) => sum + s.conversions, 0) ?? 0;
  const overallCR =
    totalClicks > 0 ? (totalConversions / totalClicks) * 100 : 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-ink">비즈니스 전략</h2>
        <p className="mt-0.5 text-sm text-ink-secondary">
          사용자 요구 미충족 영역과 수익 전환 지표를 한눈에 확인합니다.
        </p>
      </div>

      {/* ① 미충족 수요 분석 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-4 w-4 text-accent-600" />
            미충족 수요 키워드
          </CardTitle>
          <CardDescription>
            사용자가 질의했으나 매칭 결과가 0건이었던 키워드입니다. 다음 정책
            수집 우선순위 설정에 활용하세요.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {demand.isLoading ? (
            <div className="p-6">
              <AdminTableSkeleton rows={6} />
            </div>
          ) : demand.isError ? (
            <div className="p-6">
              <AdminErrorState
                message={(demand.error as unknown as ApiError)?.message}
                onRetry={() => demand.refetch()}
              />
            </div>
          ) : demandItems.length === 0 ? (
            <AdminEmptyState
              icon={Search}
              title="미충족 수요 데이터가 없습니다"
              description="채팅 로그가 축적되면 분석 결과가 표시됩니다."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-muted text-xs font-semibold uppercase text-ink-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left">순위</th>
                    <th className="px-4 py-3 text-left">키워드</th>
                    <th className="px-4 py-3 text-right">질의 건수</th>
                    <th className="px-4 py-3 text-left">최근 질의</th>
                    <th className="px-4 py-3 text-left">관련 업종</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {demandItems.map((k, idx) => (
                    <tr key={k.keyword} className="hover:bg-surface-muted/50">
                      <td className="px-4 py-3 font-semibold text-primary-700 numeric">
                        #{(page - 1) * 20 + idx + 1}
                      </td>
                      <td className="px-4 py-3 font-medium text-ink">
                        {k.keyword}
                      </td>
                      <td className="px-4 py-3 text-right numeric font-semibold text-accent-700">
                        {k.query_count.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-tertiary">
                        {new Date(k.last_asked_at).toLocaleDateString("ko-KR")}
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-secondary">
                        {k.related_sector_codes?.join(", ") ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {demandTotal > 0 && (
        <p className="text-right text-xs text-ink-tertiary numeric">
          총 {demandTotal.toLocaleString()}개 키워드
        </p>
      )}

      {demandPages > 1 && (
        <AdminPagination
          page={page}
          totalPages={demandPages}
          onChange={setPage}
        />
      )}

      {/* ② 수익 전환 통계 */}
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-end justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              수익 전환 통계
            </CardTitle>
            <CardDescription>
              전문가 상담 예약 및 솔루션(로봇·키오스크 등) 클릭/전환 리포트.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-ink-tertiary" />
              <Label className="mb-0 text-xs">기간</Label>
            </div>
            <Input
              type="date"
              className="h-9 w-36"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
            <span className="text-ink-tertiary">~</span>
            <Input
              type="date"
              className="h-9 w-36"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          {conversion.isLoading ? (
            <AdminTableSkeleton rows={4} />
          ) : conversion.isError ? (
            <AdminErrorState
              message={(conversion.error as unknown as ApiError)?.message}
              onRetry={() => conversion.refetch()}
            />
          ) : !conv ? (
            <AdminEmptyState
              icon={TrendingUp}
              title="전환 데이터가 없습니다"
              description="해당 기간의 예약·클릭 데이터가 없습니다."
            />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <StatCard
                  icon={MessagesSquare}
                  tone="primary"
                  label="전문가 상담 예약"
                  value={`${conv.consultation_bookings.toLocaleString()}건`}
                />
                <StatCard
                  icon={ShoppingBag}
                  tone="warning"
                  label="솔루션 클릭"
                  value={totalClicks.toLocaleString()}
                />
                <StatCard
                  icon={TrendingUp}
                  tone="success"
                  label="전환"
                  value={totalConversions.toLocaleString()}
                />
                <StatCard
                  icon={TrendingUp}
                  tone="primary"
                  label="전체 전환율"
                  value={`${overallCR.toFixed(1)}%`}
                  hint={
                    conv.revenue_estimate_krw != null
                      ? `예상 매출 ₩${Math.round(
                          conv.revenue_estimate_krw
                        ).toLocaleString()}`
                      : undefined
                  }
                />
              </div>

              {/* 솔루션별 차트 */}
              {solutionChart.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase text-ink-tertiary">
                    솔루션별 클릭 · 전환
                  </p>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={solutionChart}>
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="#E2E8F0"
                          vertical={false}
                        />
                        <XAxis
                          dataKey="name"
                          tick={{ fontSize: 11, fill: "#475569" }}
                          tickLine={false}
                        />
                        <YAxis
                          tick={{ fontSize: 11, fill: "#475569" }}
                          tickLine={false}
                          allowDecimals={false}
                        />
                        <Tooltip
                          contentStyle={{
                            borderRadius: 8,
                            border: "1px solid #E2E8F0",
                            fontSize: 12,
                          }}
                        />
                        <Bar
                          dataKey="클릭"
                          fill="#93C5FD"
                          radius={[4, 4, 0, 0]}
                        />
                        <Bar
                          dataKey="전환"
                          fill="#2563EB"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* 솔루션별 테이블 */}
              {conv.solution_clicks.length > 0 && (
                <div className="overflow-hidden rounded-lg border border-surface-border">
                  <table className="w-full text-sm">
                    <thead className="bg-surface-muted text-xs font-semibold uppercase text-ink-secondary">
                      <tr>
                        <th className="px-4 py-2 text-left">솔루션</th>
                        <th className="px-4 py-2 text-right">클릭</th>
                        <th className="px-4 py-2 text-right">전환</th>
                        <th className="px-4 py-2 text-right">전환율</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border">
                      {conv.solution_clicks.map((s) => (
                        <tr key={s.solution_key}>
                          <td className="px-4 py-2.5 font-medium text-ink">
                            {s.solution_label}
                          </td>
                          <td className="px-4 py-2.5 text-right numeric">
                            {s.clicks.toLocaleString()}
                          </td>
                          <td className="px-4 py-2.5 text-right numeric">
                            {s.conversions.toLocaleString()}
                          </td>
                          <td className="px-4 py-2.5 text-right numeric font-semibold text-primary-700">
                            {s.conversion_rate_pct.toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
