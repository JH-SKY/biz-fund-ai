"use client";

import * as React from "react";
import {
  Activity,
  AlertCircle,
  DollarSign,
  Filter,
  Gauge,
  GitCompare,
  MessageSquareText,
  MousePointerClick,
  Route,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AdminGuard, AdminShell } from "@/components/admin";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Tabs } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  AdminEmptyState,
  AdminTableSkeleton,
  StatCard,
  SystemStatusBadge,
} from "@/features/admin";
import {
  useAgentNodes,
  useAgentOverview,
  useAgentRunDetail,
  useAgentRuns,
  useLatencyTimeSeries,
  useSystemHealth,
} from "@/hooks/useAdmin";
import { cn } from "@/lib/utils";
import type { AgentMonitoringFilters, MonitoringRange } from "@/types";

const FALLBACK_OPTIONS = [
  { value: "all", label: "전체" },
  { value: "true", label: "Fallback만" },
  { value: "false", label: "Fallback 제외" },
];

const STATUS_OPTIONS = [
  { value: "", label: "전체" },
  { value: "SUCCESS", label: "SUCCESS" },
  { value: "ERROR", label: "ERROR" },
];

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
  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);
  const [intent, setIntent] = React.useState("");
  const [model, setModel] = React.useState("");
  const [fallbackValue, setFallbackValue] = React.useState<"all" | "true" | "false">("all");
  const [status, setStatus] = React.useState("");

  const filters = React.useMemo<AgentMonitoringFilters>(() => {
    const next: AgentMonitoringFilters = {};
    if (intent) next.intent = intent;
    if (model) next.model = model;
    if (status) next.status = status;
    if (fallbackValue === "true") next.fallback = true;
    if (fallbackValue === "false") next.fallback = false;
    return next;
  }, [fallbackValue, intent, model, status]);

  const health = useSystemHealth();
  const latency = useLatencyTimeSeries(range);
  const agentOverview = useAgentOverview(range, filters);
  const agentNodes = useAgentNodes(range, filters);
  const agentRuns = useAgentRuns({ range, page: 1, size: 12, ...filters });
  const agentRunDetail = useAgentRunDetail(selectedRunId);

  const overview = agentOverview.data;
  const nodes = agentNodes.data;
  const runs = agentRuns.data;
  const detail = agentRunDetail.data;

  React.useEffect(() => {
    if (!selectedRunId && runs?.items?.length) {
      setSelectedRunId(runs.items[0].run_id);
    }
  }, [runs?.items, selectedRunId]);

  React.useEffect(() => {
    if (selectedRunId && runs?.items?.every((item) => item.run_id !== selectedRunId)) {
      setSelectedRunId(runs.items[0]?.run_id ?? null);
    }
  }, [runs?.items, selectedRunId]);

  const latencyChart =
    latency.data?.points.map((point) => ({
      time: point.timestamp
        ? new Date(point.timestamp).toLocaleString("ko-KR", {
            month: range === "30d" || range === "7d" ? "numeric" : undefined,
            day: range === "30d" || range === "7d" ? "numeric" : undefined,
            hour: "2-digit",
            minute: "2-digit",
          })
        : "-",
      p50: point.p50_ms,
      p95: point.p95_ms,
      count: point.count,
    })) ?? [];

  const intentOptions = React.useMemo(
    () =>
      (overview?.by_intent ?? []).map((row) => ({
        value: row.intent,
        label: `${row.intent} (${row.runs})`,
      })),
    [overview?.by_intent]
  );

  const modelOptions = React.useMemo(
    () =>
      (overview?.by_model ?? []).map((row) => ({
        value: row.model,
        label: `${row.model} (${row.runs})`,
      })),
    [overview?.by_model]
  );

  const hottestIntent = overview?.by_intent?.[0] ?? null;
  const mostExpensiveIntent = React.useMemo(() => {
    const intents = overview?.by_intent ?? [];
    if (!intents.length) return null;
    return [...intents].sort((a, b) => b.cost_usd - a.cost_usd)[0];
  }, [overview?.by_intent]);
  const bottleneckNode = React.useMemo(() => {
    const items = nodes?.items ?? [];
    if (!items.length) return null;
    return [...items].sort((a, b) => b.p95_latency_ms - a.p95_latency_ms)[0];
  }, [nodes?.items]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">BizMong 관측 모니터링</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            질문 1건을 run/node 단위로 추적하고, 병목 node와 비싼 route를 바로 찾는 화면입니다.
          </p>
        </div>
        <Tabs
          size="sm"
          value={range}
          onValueChange={(value) => setRange(value as MonitoringRange)}
          items={[
            { value: "1h", label: "1시간" },
            { value: "24h", label: "24시간" },
            { value: "7d", label: "7일" },
            { value: "30d", label: "30일" },
          ]}
        />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-4 w-4 text-primary-600" />
            관측 필터
          </CardTitle>
          <CardDescription>intent, model, fallback, status를 같이 좁혀서 runs, nodes, 비용을 같은 기준으로 봅니다.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Select
            value={intent}
            onChange={(event) => setIntent(event.target.value)}
            options={intentOptions}
            placeholder="intent 전체"
          />
          <Select
            value={model}
            onChange={(event) => setModel(event.target.value)}
            options={modelOptions}
            placeholder="model 전체"
          />
          <Select
            value={fallbackValue}
            onChange={(event) => setFallbackValue(event.target.value as "all" | "true" | "false")}
            options={FALLBACK_OPTIONS}
          />
          <Select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            options={STATUS_OPTIONS}
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-4 p-6 lg:flex-row lg:items-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-50 text-primary-700">
            <Activity className="h-7 w-7" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-tertiary">시스템 상태</p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <SystemStatusBadge status={health.data?.status ?? "UNKNOWN"} />
              <span className="text-sm text-ink-secondary">
                uptime <b className="numeric">{health.data?.uptime_pct?.toFixed(2) ?? "--"}%</b>
              </span>
              <span className="text-sm text-ink-secondary">
                error <b className="numeric">{health.data?.error_rate_pct?.toFixed(2) ?? "--"}%</b>
              </span>
              {health.data?.last_incident_at && (
                <span className="text-xs text-ink-tertiary">
                  최근 이슈 {new Date(health.data.last_incident_at).toLocaleString("ko-KR")}
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={MessageSquareText}
          tone="primary"
          label="총 runs"
          value={overview ? `${overview.total_runs}` : "--"}
          hint="질문 1건 = run 1건"
          isLoading={agentOverview.isLoading}
        />
        <StatCard
          icon={Gauge}
          tone="success"
          label="성공률"
          value={overview ? `${overview.success_rate_pct.toFixed(1)}%` : "--"}
          hint={overview ? `fallback ${overview.quality_metrics?.fallback_rate_pct.toFixed(1) ?? "0.0"}%` : "집계 중"}
          isLoading={agentOverview.isLoading}
        />
        <StatCard
          icon={DollarSign}
          tone="warning"
          label="총 비용"
          value={overview ? `₩${Math.round(overview.total_cost_krw).toLocaleString()}` : "--"}
          hint={overview ? `$${overview.total_cost_usd.toFixed(4)}` : "집계 중"}
          isLoading={agentOverview.isLoading}
        />
        <StatCard
          icon={Zap}
          tone="danger"
          label="CTA 클릭"
          value={overview ? `${overview.cta_clicks}` : "--"}
          hint={overview ? `피드백 ${overview.dislike_feedback_count}` : "집계 중"}
          isLoading={agentOverview.isLoading}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={Gauge}
          tone="primary"
          label="평균 latency"
          value={overview ? `${overview.avg_latency_ms}ms` : "--"}
          hint="run 기준"
          isLoading={agentOverview.isLoading}
        />
        <StatCard
          icon={Gauge}
          tone="warning"
          label="p50 latency"
          value={overview ? `${overview.p50_latency_ms}ms` : "--"}
          hint="중앙값"
          isLoading={agentOverview.isLoading}
        />
        <StatCard
          icon={AlertCircle}
          tone="danger"
          label="p95 latency"
          value={overview ? `${overview.p95_latency_ms}ms` : "--"}
          hint="상위 5%"
          isLoading={agentOverview.isLoading}
        />
        <StatCard
          icon={Route}
          tone="success"
          label="총 token"
          value={
            overview
              ? `${((overview.total_tokens_in ?? 0) + (overview.total_tokens_out ?? 0)).toLocaleString()}`
              : "--"
          }
          hint={overview ? `in ${overview.total_tokens_in.toLocaleString()} / out ${overview.total_tokens_out.toLocaleString()}` : "집계 중"}
          isLoading={agentOverview.isLoading}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <InsightCard
          icon={TrendingUp}
          title="가장 비싼 intent"
          body={
            mostExpensiveIntent
              ? `${mostExpensiveIntent.intent} · $${mostExpensiveIntent.cost_usd.toFixed(4)}`
              : "데이터 없음"
          }
          sub={
            mostExpensiveIntent
              ? `avg ${mostExpensiveIntent.avg_latency_ms}ms / error ${mostExpensiveIntent.error_rate_pct.toFixed(1)}%`
              : "질문이 쌓이면 route별 비용이 보입니다."
          }
        />
        <InsightCard
          icon={Gauge}
          title="병목 node"
          body={bottleneckNode ? `${bottleneckNode.node_name} · p95 ${bottleneckNode.p95_latency_ms}ms` : "데이터 없음"}
          sub={
            bottleneckNode
              ? `avg ${bottleneckNode.avg_latency_ms}ms / error ${bottleneckNode.error_rate_pct.toFixed(1)}%`
              : "node 실행이 쌓이면 병목이 보입니다."
          }
        />
        <InsightCard
          icon={MessageSquareText}
          title="가장 많이 들어온 질문군"
          body={hottestIntent ? `${hottestIntent.intent} · ${hottestIntent.runs} runs` : "데이터 없음"}
          sub={
            hottestIntent
              ? `avg ${hottestIntent.avg_latency_ms}ms / $${hottestIntent.cost_usd.toFixed(4)}`
              : "질문이 쌓이면 집중 구간이 보입니다."
          }
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Latency 추이</CardTitle>
          <CardDescription>스트리밍 기준 응답시간 변화를 p50 / p95로 봅니다.</CardDescription>
        </CardHeader>
        <CardContent className="h-80">
          {latency.isLoading ? (
            <AdminTableSkeleton rows={6} />
          ) : latencyChart.length === 0 ? (
            <AdminEmptyState
              icon={TrendingUp}
              title="아직 관측 데이터가 없습니다"
              description="run이 쌓이면 시간대별 latency 추이가 보입니다."
            />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latencyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#475569" }} tickLine={false} />
                <YAxis yAxisId="latency" tick={{ fontSize: 11, fill: "#475569" }} tickLine={false} unit="ms" />
                <YAxis yAxisId="count" orientation="right" tick={{ fontSize: 11, fill: "#475569" }} tickLine={false} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line yAxisId="latency" type="monotone" dataKey="p50" name="P50" stroke="#2563EB" strokeWidth={2} dot={false} />
                <Line yAxisId="latency" type="monotone" dataKey="p95" name="P95" stroke="#F59E0B" strokeWidth={2} dot={false} />
                <Line yAxisId="count" type="monotone" dataKey="count" name="Runs" stroke="#10B981" strokeWidth={2} dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <MetricTableCard
          title="Intent별 비용 / 지연"
          description="어느 질문군이 비싼지 바로 볼 수 있게 정렬 없이도 비교 가능한 표입니다."
          isLoading={agentOverview.isLoading}
          isEmpty={!overview || overview.by_intent.length === 0}
          emptyTitle="intent 집계가 없습니다"
          emptyDescription="BizMong run이 쌓이면 route별 비교가 보입니다."
          headers={["Intent", "Runs", "Avg ms", "Cost", "Error %"]}
          rows={(overview?.by_intent ?? []).map((row) => [
            row.intent,
            row.runs.toLocaleString(),
            `${row.avg_latency_ms}ms`,
            `$${row.cost_usd.toFixed(4)}`,
            `${row.error_rate_pct.toFixed(1)}%`,
          ])}
        />

        <MetricTableCard
          title="Node별 병목"
          description="router, general_qa, rag_retrieval, rag_generation, stats 중 어디가 느린지 봅니다."
          isLoading={agentNodes.isLoading}
          isEmpty={!nodes || nodes.items.length === 0}
          emptyTitle="node 집계가 없습니다"
          emptyDescription="node 로그가 쌓이면 병목이 바로 드러납니다."
          headers={["Node", "Exec", "Avg ms", "P95 ms", "Cost", "Error %"]}
          rows={(nodes?.items ?? []).map((row) => [
            row.node_name,
            row.executions.toLocaleString(),
            `${row.avg_latency_ms}ms`,
            `${row.p95_latency_ms}ms`,
            `$${row.cost_usd.toFixed(4)}`,
            `${row.error_rate_pct.toFixed(1)}%`,
          ])}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">최근 실행 로그</CardTitle>
            <CardDescription>행을 클릭하면 오른쪽에서 node 타임라인과 CTA 전환까지 상세 드릴다운을 봅니다.</CardDescription>
          </CardHeader>
          <CardContent>
            {!runs || runs.items.length === 0 ? (
              <AdminEmptyState
                icon={MessageSquareText}
                title="최근 실행 로그가 없습니다"
                description="질문이 들어오면 turn 단위 로그가 여기에 보입니다."
              />
            ) : (
              <div className="overflow-hidden rounded-lg border border-surface-border">
                <table className="w-full text-sm">
                  <thead className="bg-surface-muted text-xs uppercase text-ink-secondary">
                    <tr>
                      <th className="px-4 py-2 text-left">시간</th>
                      <th className="px-4 py-2 text-left">질문</th>
                      <th className="px-4 py-2 text-left">Route</th>
                      <th className="px-4 py-2 text-left">Status</th>
                      <th className="px-4 py-2 text-right">Latency</th>
                      <th className="px-4 py-2 text-right">Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {runs.items.map((row) => (
                      <tr
                        key={row.run_id}
                        className={cn("cursor-pointer transition-colors hover:bg-primary-50", selectedRunId === row.run_id && "bg-primary-50")}
                        onClick={() => setSelectedRunId(row.run_id)}
                      >
                        <td className="px-4 py-3 text-xs text-ink-secondary">
                          {row.created_at ? new Date(row.created_at).toLocaleString("ko-KR") : "-"}
                        </td>
                        <td className="max-w-[320px] px-4 py-3 text-ink">
                          <div className="line-clamp-2">{row.question_preview ?? "-"}</div>
                        </td>
                        <td className="px-4 py-3">{row.route_intent ?? "-"}</td>
                        <td className="px-4 py-3">
                          <Badge variant={row.status === "SUCCESS" ? "success" : "danger"} size="sm">
                            {row.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right numeric">{row.total_latency_ms ?? 0}ms</td>
                        <td className="px-4 py-3 text-right numeric">${row.total_cost_usd.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">실행 상세</CardTitle>
            <CardDescription>선택한 질문 1건의 route, 버전, node, CTA 클릭을 한 번에 봅니다.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedRunId || !detail ? (
              <AdminEmptyState
                icon={MessageSquareText}
                title="실행 로그를 선택해 주세요"
                description="왼쪽 표에서 한 건을 클릭하면 상세 타임라인이 열립니다."
              />
            ) : (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <MiniMetric label="Route" value={detail.run.route_intent ?? "-"} />
                  <MiniMetric label="Final Agent" value={detail.run.final_agent ?? "-"} />
                  <MiniMetric label="Latency" value={`${detail.run.total_latency_ms ?? 0}ms`} />
                  <MiniMetric label="Cost" value={`$${detail.run.total_cost_usd.toFixed(4)}`} />
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <MiniMetric label="Prompt Version" value={detail.run.prompt_version ?? "-"} />
                  <MiniMetric label="Graph Version" value={detail.run.graph_version ?? "-"} />
                  <MiniMetric label="RAG Version" value={detail.run.rag_strategy_version ?? "-"} />
                </div>

                <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
                  <p className="text-xs uppercase text-ink-tertiary">Question Preview</p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{detail.run.question_preview ?? "-"}</p>
                </div>

                <MetricTableCard
                  title="Node Timeline"
                  description=""
                  compact
                  isLoading={agentRunDetail.isLoading}
                  isEmpty={detail.nodes.length === 0}
                  emptyTitle="node 로그가 없습니다"
                  emptyDescription="이 run에 기록된 node가 없습니다."
                  headers={["Seq", "Node", "Model", "Latency", "Tokens", "Cost"]}
                  rows={detail.nodes.map((node) => [
                    `${node.sequence}`,
                    node.node_name,
                    node.model_name ?? "-",
                    `${node.latency_ms ?? 0}ms`,
                    `${((node.tokens_in ?? 0) + (node.tokens_out ?? 0)).toLocaleString()}`,
                    `$${node.cost_usd.toFixed(4)}`,
                  ])}
                />

                <MetricTableCard
                  title="CTA 전환 로그"
                  description=""
                  compact
                  isLoading={agentRunDetail.isLoading}
                  isEmpty={detail.cta_events.length === 0}
                  emptyTitle="CTA 클릭이 없습니다"
                  emptyDescription="이 답변 이후 발생한 페이지 이동이 아직 없습니다."
                  headers={["CTA", "Target", "시간"]}
                  rows={detail.cta_events.map((event) => [
                    event.cta_type,
                    event.target_path,
                    event.created_at ? new Date(event.created_at).toLocaleString("ko-KR") : "-",
                  ])}
                />
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <VersionCard title="Prompt 비교" items={overview?.by_prompt_version ?? []} />
        <VersionCard title="Graph 비교" items={overview?.by_graph_version ?? []} />
        <VersionCard title="RAG 전략 비교" items={overview?.by_rag_strategy_version ?? []} />
      </div>
    </div>
  );
}

function InsightCard({
  icon: Icon,
  title,
  body,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
  sub: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3 p-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-50 text-primary-700">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-tertiary">{title}</p>
          <p className="mt-1 text-sm font-semibold text-ink">{body}</p>
          <p className="mt-1 text-xs text-ink-secondary">{sub}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function MetricTableCard({
  title,
  description,
  headers,
  rows,
  isLoading,
  isEmpty,
  emptyTitle,
  emptyDescription,
  compact = false,
}: {
  title: string;
  description: string;
  headers: string[];
  rows: string[][];
  isLoading: boolean;
  isEmpty: boolean;
  emptyTitle: string;
  emptyDescription: string;
  compact?: boolean;
}) {
  return (
    <Card>
      {title ? (
        <CardHeader className={compact ? "pb-3" : undefined}>
          <CardTitle className="text-base">{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </CardHeader>
      ) : null}
      <CardContent className={compact ? "pt-0" : undefined}>
        {isLoading ? (
          <AdminTableSkeleton rows={4} />
        ) : isEmpty ? (
          <AdminEmptyState icon={AlertCircle} title={emptyTitle} description={emptyDescription} />
        ) : (
          <div className="overflow-hidden rounded-lg border border-surface-border">
            <table className="w-full text-sm">
              <thead className="bg-surface-muted text-xs uppercase text-ink-secondary">
                <tr>
                  {headers.map((header) => (
                    <th key={header} className="px-4 py-2 text-left">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {rows.map((row, index) => (
                  <tr key={`${title}-${index}`}>
                    {row.map((cell, cellIndex) => (
                      <td key={`${title}-${index}-${cellIndex}`} className={cn("px-4 py-2.5", cellIndex > 0 && cellIndex === row.length - 1 && "numeric")}>
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-surface-border px-3 py-3">
      <p className="text-xs uppercase text-ink-tertiary">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink">{value}</p>
    </div>
  );
}

function VersionCard({
  title,
  items,
}: {
  title: string;
  items: Array<{ version: string; runs: number; avg_latency_ms: number; cost_usd: number }>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <GitCompare className="h-4 w-4 text-primary-600" />
          {title}
        </CardTitle>
        <CardDescription>개선 전 vs 개선 후 비교에 바로 쓸 수 있는 버전 축입니다.</CardDescription>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <AdminEmptyState
            icon={MousePointerClick}
            title="버전 데이터가 없습니다"
            description="run이 쌓이면 버전별 비용과 latency를 바로 비교할 수 있습니다."
          />
        ) : (
          <div className="space-y-2">
            {items.slice(0, 5).map((item) => (
              <div key={`${title}-${item.version}`} className="rounded-lg border border-surface-border px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-semibold text-ink">{item.version}</p>
                  <Badge variant="outline" size="sm">
                    {item.runs} runs
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-ink-secondary">
                  avg {item.avg_latency_ms}ms · ${item.cost_usd.toFixed(4)}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
