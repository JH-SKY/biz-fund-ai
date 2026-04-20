"use client";

/**
 * /admin/monitoring — 시스템 건강 상태 & AI 비용 모니터링.
 *
 * 기능 (PAGE 12 ②)
 *  - 실시간 신호등 (🟢/🟡/🔴) + 컴포넌트별 상태
 *  - p50/p95 레이턴시 & 에러율 라인 차트 (1h/24h/7d 토글)
 *  - 오늘의 AI 토큰 비용 & 모델별 상세
 */

import * as React from "react";
import {
  Activity,
  AlertCircle,
  DollarSign,
  Gauge,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
  XAxis,
  YAxis,
  Legend,
} from "recharts";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminTableSkeleton,
  StatCard,
  SystemStatusBadge,
} from "@/features/admin";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import {
  useLatencyTimeSeries,
  useSystemHealth,
  useTokenCost,
} from "@/hooks/useAdmin";
import type { MonitoringRange } from "@/types";

export default function AdminMonitoringPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <MonitoringContent />
      </AdminShell>
    </AdminGuard>
  );
}

function MonitoringContent() {
  const [range, setRange] = React.useState<MonitoringRange>("24h");
  const health = useSystemHealth();
  const latency = useLatencyTimeSeries(range);
  const cost = useTokenCost();

  const healthData = health.data;
  const costData = cost.data;

  const latencyChart =
    latency.data?.points.map((p) => ({
      time: new Date(p.timestamp).toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      p50: p.p50_ms,
      p95: p.p95_ms,
      errorRate: p.error_rate_pct,
    })) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-ink">
          시스템 건강 상태 & 비용 모니터링
        </h2>
        <p className="mt-0.5 text-sm text-ink-secondary">
          비즈몽의 응답 속도·에러·AI 모델 비용을 실시간으로 감시합니다.
        </p>
      </div>

      {/* 전체 시스템 상태 */}
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-6 sm:flex-row sm:items-center sm:gap-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-50 text-primary-700">
            <Activity className="h-8 w-8" />
          </div>
          <div className="flex-1 text-center sm:text-left">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-tertiary">
              전체 서비스 상태
            </p>
            <div className="mt-1 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              {health.isLoading ? (
                <span className="text-lg font-semibold text-ink-tertiary">
                  확인 중…
                </span>
              ) : (
                <>
                  <SystemStatusBadge status={healthData?.status ?? "UNKNOWN"} />
                  <span className="text-xs text-ink-secondary">
                    업타임{" "}
                    <b className="numeric">
                      {healthData?.uptime_pct?.toFixed(2) ?? "—"}%
                    </b>
                  </span>
                  {healthData?.last_incident_at && (
                    <span className="text-xs text-ink-tertiary">
                      · 마지막 이슈{" "}
                      {new Date(
                        healthData.last_incident_at
                      ).toLocaleString("ko-KR")}
                    </span>
                  )}
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 주요 지표 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={Gauge}
          tone="primary"
          label="P50 레이턴시"
          value={
            healthData ? `${healthData.latency_p50_ms}ms` : "—"
          }
          hint="중간값"
          isLoading={health.isLoading}
        />
        <StatCard
          icon={Gauge}
          tone="warning"
          label="P95 레이턴시"
          value={
            healthData ? `${healthData.latency_p95_ms}ms` : "—"
          }
          hint="상위 5%"
          isLoading={health.isLoading}
        />
        <StatCard
          icon={AlertCircle}
          tone="danger"
          label="오류 발생률"
          value={
            healthData
              ? `${healthData.error_rate_pct.toFixed(2)}%`
              : "—"
          }
          hint="최근 5분"
          isLoading={health.isLoading}
        />
        <StatCard
          icon={DollarSign}
          tone="success"
          label="오늘 AI 비용"
          value={
            costData
              ? `₩${Math.round(costData.total_krw).toLocaleString()}`
              : "—"
          }
          hint={
            costData
              ? `$${costData.total_usd.toFixed(2)} · ${(
                  costData.total_tokens_in + costData.total_tokens_out
                ).toLocaleString()} tokens`
              : "집계 중"
          }
          isLoading={cost.isLoading}
        />
      </div>

      {/* 컴포넌트 상태 */}
      {healthData?.components && healthData.components.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">구성 요소별 상태</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {healthData.components.map((c) => (
              <div
                key={c.name}
                className="flex items-center justify-between rounded-lg border border-surface-border px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-ink">{c.name}</p>
                  {c.message && (
                    <p className="text-[11px] text-ink-tertiary">
                      {c.message}
                    </p>
                  )}
                </div>
                <SystemStatusBadge status={c.status} size="sm" />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 레이턴시/에러 차트 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              응답 속도 & 에러 추이
            </CardTitle>
            <CardDescription>
              비즈몽 에이전트 종단간 응답 시간
            </CardDescription>
          </div>
          <Tabs
            size="sm"
            value={range}
            onValueChange={(v) => setRange(v as MonitoringRange)}
            items={[
              { value: "1h", label: "1시간" },
              { value: "24h", label: "24시간" },
              { value: "7d", label: "7일" },
              { value: "30d", label: "30일" },
            ]}
          />
        </CardHeader>
        <CardContent className="h-80">
          {latency.isLoading ? (
            <AdminTableSkeleton rows={6} />
          ) : latencyChart.length === 0 ? (
            <AdminEmptyState
              icon={TrendingUp}
              title="집계된 데이터가 없습니다"
              description="측정 데이터가 쌓이면 차트로 표시됩니다."
            />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latencyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  tickLine={false}
                />
                <YAxis
                  yAxisId="ms"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  tickLine={false}
                  unit="ms"
                />
                <YAxis
                  yAxisId="rate"
                  orientation="right"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  tickLine={false}
                  unit="%"
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #E2E8F0",
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line
                  yAxisId="ms"
                  type="monotone"
                  dataKey="p50"
                  name="P50 ms"
                  stroke="#2563EB"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="ms"
                  type="monotone"
                  dataKey="p95"
                  name="P95 ms"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="rate"
                  type="monotone"
                  dataKey="errorRate"
                  name="에러율 %"
                  stroke="#EF4444"
                  strokeWidth={2}
                  dot={false}
                  strokeDasharray="4 4"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* 모델별 비용 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap className="h-4 w-4 text-accent-600" />
            AI 모델별 비용 (오늘)
          </CardTitle>
          <CardDescription>
            비용은 입력/출력 토큰 단가를 기준으로 환산한 추정치입니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {cost.isLoading ? (
            <AdminTableSkeleton rows={3} />
          ) : !costData || costData.by_model.length === 0 ? (
            <AdminEmptyState
              icon={DollarSign}
              title="집계된 비용이 없습니다"
              description="오늘 집계된 API 호출이 있으면 여기에 표시됩니다."
            />
          ) : (
            <div className="overflow-hidden rounded-lg border border-surface-border">
              <table className="w-full text-sm">
                <thead className="bg-surface-muted text-xs font-semibold uppercase text-ink-secondary">
                  <tr>
                    <th className="px-4 py-2 text-left">모델</th>
                    <th className="px-4 py-2 text-right">입력 토큰</th>
                    <th className="px-4 py-2 text-right">출력 토큰</th>
                    <th className="px-4 py-2 text-right">비용 (USD)</th>
                    <th className="px-4 py-2 text-right">비용 (KRW)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {costData.by_model.map((row) => (
                    <tr key={row.model} className="bg-surface">
                      <td className="px-4 py-2.5 font-medium text-ink">
                        {row.model}
                      </td>
                      <td className="px-4 py-2.5 text-right numeric text-ink-secondary">
                        {row.tokens_in.toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 text-right numeric text-ink-secondary">
                        {row.tokens_out.toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 text-right numeric text-ink">
                        ${row.cost_usd.toFixed(4)}
                      </td>
                      <td className="px-4 py-2.5 text-right numeric font-semibold text-primary-700">
                        ₩{Math.round(row.cost_krw).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-primary-50 font-semibold">
                    <td className="px-4 py-2.5 text-primary-900">합계</td>
                    <td className="px-4 py-2.5 text-right numeric">
                      {costData.total_tokens_in.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right numeric">
                      {costData.total_tokens_out.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right numeric">
                      ${costData.total_usd.toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 text-right numeric text-primary-900">
                      ₩{Math.round(costData.total_krw).toLocaleString()}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
