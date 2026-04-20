"use client";

/**
 * /admin/dashboard — 통합 관리 센터 홈.
 *
 * 구성 (PAGE 12 기획안 기반)
 *  1) 시스템 신호등 + 주요 지표(3종 Stat)
 *  2) 인기 정책 Bar 차트
 *  3) 최근 피드백 / 최근 배치 / 미충족 수요 키워드 미리보기 (CTA → 상세 페이지)
 *
 * "결론 먼저" 원칙에 따라 최상단엔 시스템 상태, 그 아래 핵심 숫자를 노출.
 */

import Link from "next/link";
import {
  Users,
  MessageSquareText,
  TrendingUp,
  BarChart3,
  ArrowRight,
  AlertTriangle,
  Search,
  Activity,
  Cpu,
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
  StatCard,
  SystemStatusBadge,
  AdminEmptyState,
  AdminTableSkeleton,
  mapBatchStatusToTone,
} from "@/features/admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useAdminDashboard,
  useAdminFeedback,
  useBatchStatus,
  useSystemHealth,
  useUnmetDemand,
} from "@/hooks/useAdmin";
import { cn } from "@/lib/utils";

export default function AdminDashboardPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <DashboardContent />
      </AdminShell>
    </AdminGuard>
  );
}

function DashboardContent() {
  const dashboard = useAdminDashboard();
  const health = useSystemHealth();
  const feedback = useAdminFeedback({
    is_resolved: false,
    page: 1,
    size: 5,
  });
  const batch = useBatchStatus();
  const unmet = useUnmetDemand(1, 5);

  const stats = dashboard.data;
  const healthData = health.data;
  const feedbackItems = feedback.data?.items ?? [];
  const batchItems = batch.data ?? [];
  const unmetItems = unmet.data?.items ?? [];

  const chartData =
    stats?.popular_policies?.slice(0, 6).map((p) => ({
      name: p.title.length > 14 ? p.title.slice(0, 14) + "…" : p.title,
      조회수: p.view_count,
    })) ?? [];

  return (
    <div className="space-y-6">
      {/* ① 시스템 상태 배너 */}
      <Card className={cn("overflow-hidden")}>
        <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary-50 text-primary-700">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-tertiary">
                실시간 시스템 상태
              </p>
              <div className="mt-1 flex items-center gap-2">
                {health.isLoading ? (
                  <span className="text-sm text-ink-tertiary">확인 중…</span>
                ) : (
                  <SystemStatusBadge status={healthData?.status ?? "UNKNOWN"} />
                )}
                {healthData && (
                  <span className="text-xs text-ink-secondary">
                    p50 <b className="numeric">{healthData.latency_p50_ms}ms</b>{" "}
                    · p95{" "}
                    <b className="numeric">{healthData.latency_p95_ms}ms</b> ·
                    오류율{" "}
                    <b className="numeric">
                      {healthData.error_rate_pct.toFixed(2)}%
                    </b>
                  </span>
                )}
              </div>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/monitoring">
              모니터링 상세
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* ② 핵심 지표 3종 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          icon={Users}
          tone="primary"
          label="오늘 신규 가입"
          value={
            stats?.new_users_today != null
              ? `${stats.new_users_today.toLocaleString()}명`
              : "—"
          }
          hint="24시간 내 가입 사용자"
          isLoading={dashboard.isLoading}
        />
        <StatCard
          icon={MessageSquareText}
          tone="success"
          label="오늘 활성 채팅"
          value={
            stats?.active_chats_today != null
              ? `${stats.active_chats_today.toLocaleString()}건`
              : "—"
          }
          hint="비즈몽 대화 세션"
          isLoading={dashboard.isLoading}
        />
        <StatCard
          icon={TrendingUp}
          tone="warning"
          label="인기 정책 수"
          value={
            stats?.popular_policies
              ? `${stats.popular_policies.length}개`
              : "—"
          }
          hint="조회수 기준 상위"
          isLoading={dashboard.isLoading}
        />
      </div>

      {/* ③ 인기 정책 차트 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary-600" />
            인기 정책 TOP {chartData.length || "—"}
          </CardTitle>
          <CardDescription>최근 조회수 기준 상위 정책 공고</CardDescription>
        </CardHeader>
        <CardContent className="h-72">
          {dashboard.isLoading ? (
            <AdminTableSkeleton rows={5} />
          ) : chartData.length === 0 ? (
            <AdminEmptyState
              icon={BarChart3}
              title="아직 집계된 인기 정책이 없습니다"
              description="사용자들이 정책을 조회하기 시작하면 이 영역에 랭킹이 표시됩니다."
            />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 12, right: 12, bottom: 8, left: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#E2E8F0"
                  vertical={false}
                />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  tickLine={false}
                  axisLine={{ stroke: "#E2E8F0" }}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "#475569" }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  cursor={{ fill: "#F1F5F9" }}
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #E2E8F0",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="조회수" fill="#2563EB" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* ④ 요약 3열 — 피드백/배치/미충족수요 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 미해결 피드백 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-danger-500" />
              미해결 피드백
            </CardTitle>
            <Link
              href="/admin/feedback"
              className="text-xs font-medium text-primary-600 hover:underline"
            >
              전체 →
            </Link>
          </CardHeader>
          <CardContent className="pt-0">
            {feedback.isLoading ? (
              <AdminTableSkeleton rows={3} />
            ) : feedbackItems.length === 0 ? (
              <p className="py-6 text-center text-sm text-ink-tertiary">
                미해결 피드백이 없습니다
              </p>
            ) : (
              <ul className="divide-y divide-surface-border">
                {feedbackItems.map((item) => (
                  <li
                    key={item.feedback_id}
                    className="py-2.5 first:pt-0 last:pb-0"
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="danger" size="sm">
                        {item.reason_label}
                      </Badge>
                      <span className="text-xs text-ink-tertiary">
                        {item.user_name ?? item.user_id.slice(0, 8)}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-ink">
                      {item.ai_response_snippet}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* 배치 작업 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Cpu className="h-4 w-4 text-primary-600" />
              최근 배치 작업
            </CardTitle>
            <Link
              href="/admin/batch"
              className="text-xs font-medium text-primary-600 hover:underline"
            >
              전체 →
            </Link>
          </CardHeader>
          <CardContent className="pt-0">
            {batch.isLoading ? (
              <AdminTableSkeleton rows={3} />
            ) : batchItems.length === 0 ? (
              <p className="py-6 text-center text-sm text-ink-tertiary">
                등록된 배치가 없습니다
              </p>
            ) : (
              <ul className="divide-y divide-surface-border">
                {batchItems.slice(0, 5).map((job) => {
                  const tone = mapBatchStatusToTone(String(job.status));
                  return (
                    <li
                      key={job.job_id}
                      className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-ink">
                          {job.job_name}
                        </p>
                        <p className="text-xs text-ink-tertiary">
                          {job.last_run
                            ? new Date(job.last_run).toLocaleString("ko-KR")
                            : "실행 기록 없음"}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "rounded-md px-2 py-0.5 text-[11px] font-semibold",
                          tone.className
                        )}
                      >
                        {tone.label}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* 미충족 수요 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Search className="h-4 w-4 text-accent-600" />
              미충족 수요 키워드
            </CardTitle>
            <Link
              href="/admin/insights"
              className="text-xs font-medium text-primary-600 hover:underline"
            >
              전체 →
            </Link>
          </CardHeader>
          <CardContent className="pt-0">
            {unmet.isLoading ? (
              <AdminTableSkeleton rows={3} />
            ) : unmetItems.length === 0 ? (
              <p className="py-6 text-center text-sm text-ink-tertiary">
                미충족 수요가 없습니다
              </p>
            ) : (
              <ul className="flex flex-wrap gap-2 py-2">
                {unmetItems.map((k) => (
                  <Badge
                    key={k.keyword}
                    variant="accent"
                    className="flex items-center gap-1"
                  >
                    <span>#{k.keyword}</span>
                    <span className="text-[10px] text-accent-700/80 numeric">
                      {k.query_count}
                    </span>
                  </Badge>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
