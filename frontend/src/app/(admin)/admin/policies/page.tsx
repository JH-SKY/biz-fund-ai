"use client";

/**
 * /admin/policies — 정책 관리.
 *
 * 기능
 *  - 4종 수집 트리거 버튼: bootstrap / daily / run(파라미터) / embed-all
 *  - 전체 정책 검색 + 테이블 조회 (기존 policy.service 재사용)
 *  - 신규 정책 등록 / 정책 수정 Dialog
 */

import * as React from "react";
import {
  Brain,
  Calendar,
  CloudDownload,
  Database,
  Edit3,
  Layers,
  Play,
  Plus,
  Search,
} from "lucide-react";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminPagination,
  AdminTableSkeleton,
} from "@/features/admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePolicySearch } from "@/hooks/usePolicies";
import {
  useCreatePolicy,
  useEmbedAll,
  useSyncBootstrap,
  useSyncDaily,
  useSyncRun,
  useUpdatePolicy,
} from "@/hooks/useAdmin";
import { useToast } from "@/providers/ToastProvider";
import type {
  AdminPolicyCreateRequest,
  AdminPolicyUpdateRequest,
  ApiError,
  PolicyListItem,
  PolicySyncRunParams,
} from "@/types";

export default function AdminPoliciesPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <PoliciesContent />
      </AdminShell>
    </AdminGuard>
  );
}

function PoliciesContent() {
  const toast = useToast();
  const [keywordInput, setKeywordInput] = React.useState("");
  const [keyword, setKeyword] = React.useState("");
  const [page, setPage] = React.useState(1);

  const [createOpen, setCreateOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<PolicyListItem | null>(
    null
  );
  const [syncRunOpen, setSyncRunOpen] = React.useState(false);

  React.useEffect(() => {
    const t = setTimeout(() => {
      setKeyword(keywordInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [keywordInput]);

  const { data, isLoading, isError, error, refetch } = usePolicySearch({
    keyword: keyword || undefined,
    page,
    size: 20,
  });

  const policies = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;
  const totalCount = data?.total_count ?? 0;

  // 트리거 mutations
  const bootstrap = useSyncBootstrap();
  const daily = useSyncDaily();
  const embedAll = useEmbedAll();

  const handleTrigger = async (
    label: string,
    fn: () => Promise<{
      inserted?: number;
      updated?: number;
      skipped?: number;
      failed?: number;
      total_processed?: number;
      embedded?: number;
      remaining?: number;
      message?: string;
    }>
  ) => {
    try {
      const res = await fn();
      const parts: string[] = [];
      if (res.inserted != null) parts.push(`신규 ${res.inserted}`);
      if (res.updated != null) parts.push(`수정 ${res.updated}`);
      if (res.embedded != null) parts.push(`임베딩 ${res.embedded}`);
      if (res.failed != null) parts.push(`실패 ${res.failed}`);
      toast.success(`${label} 완료`, {
        message: parts.length > 0 ? parts.join(" · ") : res.message,
      });
      refetch();
    } catch (err) {
      toast.error(`${label} 실패`, {
        message: (err as unknown as ApiError).message,
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">정책 관리</h2>
          <p className="mt-0.5 text-sm text-ink-secondary">
            정책 공고를 수집·수정·임베딩합니다.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          정책 수기 등록
        </Button>
      </div>

      {/* 데이터 수집 트리거 */}
      <Card className="border-primary-200 bg-primary-50/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Database className="h-4 w-4 text-primary-600" />
            정책 데이터 수집 & 임베딩
          </CardTitle>
          <CardDescription>
            외부 API(기업마당)에서 정책을 가져오거나, 기존 정책을 벡터화합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SyncTriggerButton
            icon={CloudDownload}
            label="부트스트랩 적재"
            hint="초기 대량 적재"
            loading={bootstrap.isPending}
            onClick={() =>
              handleTrigger("부트스트랩 적재", () => bootstrap.mutateAsync())
            }
          />
          <SyncTriggerButton
            icon={Calendar}
            label="일일 동기화"
            hint="오늘 신규 공고만"
            loading={daily.isPending}
            onClick={() =>
              handleTrigger("일일 동기화", () => daily.mutateAsync())
            }
          />
          <SyncTriggerButton
            icon={Play}
            label="범위 지정 수집"
            hint="페이지·날짜 지정"
            onClick={() => setSyncRunOpen(true)}
          />
          <SyncTriggerButton
            icon={Brain}
            label="전체 임베딩"
            hint="미임베딩 일괄"
            loading={embedAll.isPending}
            onClick={() =>
              handleTrigger("임베딩", () => embedAll.mutateAsync(undefined))
            }
          />
        </CardContent>
      </Card>

      {/* 검색 + 리스트 */}
      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <div className="flex-1">
            <Input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              placeholder="정책명 검색"
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
          <span className="text-xs text-ink-tertiary numeric">
            {totalCount.toLocaleString()}건
          </span>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6">
              <AdminTableSkeleton rows={6} />
            </div>
          ) : isError ? (
            <div className="p-6">
              <AdminErrorState
                message={(error as unknown as ApiError)?.message}
                onRetry={() => refetch()}
              />
            </div>
          ) : policies.length === 0 ? (
            <AdminEmptyState
              icon={Layers}
              title="조회된 정책이 없습니다"
              description="수집 트리거 버튼으로 정책을 추가해보세요."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-muted text-xs font-semibold uppercase text-ink-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left">제목</th>
                    <th className="px-4 py-3 text-left">카테고리</th>
                    <th className="px-4 py-3 text-left">마감</th>
                    <th className="px-4 py-3 text-right">관리</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {policies.map((p) => (
                    <tr key={p.policy_id} className="hover:bg-surface-muted/50">
                      <td className="px-4 py-3">
                        <p className="font-medium text-ink">{p.title}</p>
                        <p className="text-[11px] text-ink-tertiary numeric">
                          #{p.policy_id.slice(0, 8)}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        {p.category ? (
                          <Badge variant="outline" size="sm">
                            {p.category}
                          </Badge>
                        ) : (
                          <span className="text-ink-tertiary">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-tertiary numeric">
                        {p.closed_at === "9999-12-31"
                          ? "상시접수"
                          : new Date(p.closed_at).toLocaleDateString("ko-KR")}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setEditTarget(p)}
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                          수정
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <AdminPagination
          page={page}
          totalPages={totalPages}
          onChange={setPage}
        />
      )}

      {/* 신규 등록 Dialog */}
      <PolicyFormDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        mode="create"
      />

      {/* 수정 Dialog */}
      <PolicyFormDialog
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        mode="edit"
        target={editTarget}
      />

      {/* 범위 수집 Dialog */}
      <SyncRunDialog
        open={syncRunOpen}
        onClose={() => setSyncRunOpen(false)}
        onComplete={() => refetch()}
      />
    </div>
  );
}

function SyncTriggerButton({
  icon: Icon,
  label,
  hint,
  onClick,
  loading,
}: {
  icon: React.ElementType;
  label: string;
  hint: string;
  onClick: () => void;
  loading?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={loading}
      onClick={onClick}
      className="group flex items-center gap-3 rounded-lg border border-primary-200 bg-surface p-3 text-left transition-colors hover:border-primary-400 hover:bg-primary-50 disabled:opacity-60"
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-primary-700 group-hover:bg-primary-600 group-hover:text-white">
        {loading ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        ) : (
          <Icon className="h-5 w-5" />
        )}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-ink">{label}</p>
        <p className="text-xs text-ink-tertiary">{hint}</p>
      </div>
    </button>
  );
}

// ── 정책 생성/수정 Dialog ─────────────────────────────────────────
function PolicyFormDialog({
  open,
  onClose,
  mode,
  target,
}: {
  open: boolean;
  onClose: () => void;
  mode: "create" | "edit";
  target?: PolicyListItem | null;
}) {
  const toast = useToast();
  const createMut = useCreatePolicy();
  const updateMut = useUpdatePolicy();

  const [form, setForm] = React.useState<AdminPolicyCreateRequest>({
    title: "",
    content: "",
    agency_name: "",
    category: "",
    apply_url: "",
    closed_at: "",
    support_amount: "",
  });

  React.useEffect(() => {
    if (open && target) {
      setForm({
        title: target.title,
        content: "",
        agency_name: "",
        category: target.category ?? "",
        apply_url: "",
        closed_at: target.closed_at,
        support_amount: "",
      });
    }
    if (open && !target) {
      setForm({
        title: "",
        content: "",
        agency_name: "",
        category: "",
        apply_url: "",
        closed_at: "",
        support_amount: "",
      });
    }
  }, [open, target]);

  const isPending = createMut.isPending || updateMut.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.agency_name.trim()) {
      toast.warning("제목과 주관기관은 필수입니다.");
      return;
    }
    const payload = { ...form };
    if (mode === "create") {
      createMut.mutate(payload, {
        onSuccess: () => {
          toast.success("정책이 등록되었습니다.");
          onClose();
        },
        onError: (err) =>
          toast.error("등록 실패", { message: (err as unknown as ApiError).message }),
      });
    } else if (target) {
      const body: AdminPolicyUpdateRequest = payload;
      updateMut.mutate(
        { policyId: target.policy_id, body },
        {
          onSuccess: () => {
            toast.success("정책이 수정되었습니다.");
            onClose();
          },
          onError: (err) =>
            toast.error("수정 실패", { message: (err as unknown as ApiError).message }),
        }
      );
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title={mode === "create" ? "정책 수기 등록" : "정책 수정"}
      description="외부 API로 수집되지 않는 공고를 직접 등록하거나 기존 공고를 보정합니다."
      className="sm:max-w-2xl"
      footer={
        <>
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={isPending}
          >
            취소
          </Button>
          <Button
            type="submit"
            form="policy-form"
            loading={isPending}
            disabled={isPending}
          >
            {mode === "create" ? "등록" : "저장"}
          </Button>
        </>
      }
    >
      <form
        id="policy-form"
        onSubmit={handleSubmit}
        className="space-y-3"
      >
        <div className="space-y-1.5">
          <Label htmlFor="p-title">제목 *</Label>
          <Input
            id="p-title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="예: 소상공인 경영안정자금"
            required
          />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="p-agency">주관기관 *</Label>
            <Input
              id="p-agency"
              value={form.agency_name}
              onChange={(e) =>
                setForm({ ...form, agency_name: e.target.value })
              }
              placeholder="소상공인시장진흥공단"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-category">카테고리</Label>
            <Input
              id="p-category"
              value={form.category ?? ""}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="융자 / 보조금 / 보증 ..."
            />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="p-amount">지원 금액</Label>
            <Input
              id="p-amount"
              value={form.support_amount ?? ""}
              onChange={(e) =>
                setForm({ ...form, support_amount: e.target.value })
              }
              placeholder="최대 7천만원"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-closed">마감일 (YYYY-MM-DD)</Label>
            <Input
              id="p-closed"
              value={form.closed_at ?? ""}
              onChange={(e) =>
                setForm({ ...form, closed_at: e.target.value })
              }
              placeholder="2026-12-31"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="p-url">신청 URL</Label>
          <Input
            id="p-url"
            value={form.apply_url ?? ""}
            onChange={(e) => setForm({ ...form, apply_url: e.target.value })}
            placeholder="https://..."
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="p-content">본문</Label>
          <textarea
            id="p-content"
            rows={6}
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            placeholder="정책 상세 설명..."
          />
        </div>
      </form>
    </Dialog>
  );
}

// ── 범위 수집 Dialog ───────────────────────────────────────────────
function SyncRunDialog({
  open,
  onClose,
  onComplete,
}: {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;
}) {
  const toast = useToast();
  const { mutate, isPending } = useSyncRun();
  const [params, setParams] = React.useState<PolicySyncRunParams>({
    page_start: 1,
    page_end: 10,
    rows_per_page: 20,
    with_ai: false,
    date_from: "",
    date_to: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutate(
      {
        ...params,
        date_from: params.date_from || undefined,
        date_to: params.date_to || undefined,
      },
      {
        onSuccess: (res) => {
          toast.success("범위 수집 완료", {
            message: `신규 ${res.inserted ?? 0} · 수정 ${
              res.updated ?? 0
            } · 실패 ${res.failed ?? 0}`,
          });
          onComplete();
          onClose();
        },
        onError: (err) => {
          toast.error("수집 실패", {
            message: (err as unknown as ApiError).message,
          });
        },
      }
    );
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title="범위 지정 정책 수집"
      description="기업마당 API 페이지·날짜 범위를 지정하여 수집합니다."
      footer={
        <>
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={isPending}
          >
            취소
          </Button>
          <Button
            type="submit"
            form="sync-run-form"
            loading={isPending}
            disabled={isPending}
          >
            <Play className="h-4 w-4" />
            실행
          </Button>
        </>
      }
    >
      <form id="sync-run-form" onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label>시작 페이지</Label>
            <Input
              type="number"
              min={1}
              value={params.page_start ?? 1}
              onChange={(e) =>
                setParams({ ...params, page_start: Number(e.target.value) })
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label>끝 페이지</Label>
            <Input
              type="number"
              min={1}
              value={params.page_end ?? 10}
              onChange={(e) =>
                setParams({ ...params, page_end: Number(e.target.value) })
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label>페이지당 건수</Label>
            <Input
              type="number"
              min={1}
              max={100}
              value={params.rows_per_page ?? 20}
              onChange={(e) =>
                setParams({ ...params, rows_per_page: Number(e.target.value) })
              }
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>시작일 (옵션)</Label>
            <Input
              type="date"
              value={params.date_from ?? ""}
              onChange={(e) =>
                setParams({ ...params, date_from: e.target.value })
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label>종료일 (옵션)</Label>
            <Input
              type="date"
              value={params.date_to ?? ""}
              onChange={(e) =>
                setParams({ ...params, date_to: e.target.value })
              }
            />
          </div>
        </div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={params.with_ai ?? false}
            onChange={(e) =>
              setParams({ ...params, with_ai: e.target.checked })
            }
            className="h-4 w-4 rounded border-surface-border text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-ink">
            수집 후 AI 임베딩까지 자동 실행
          </span>
        </label>
      </form>
    </Dialog>
  );
}
