"use client";

/**
 * /admin/users — 유저 관리.
 *
 * 기능
 *  - 키워드 검색 (debounce)
 *  - 비활성 유저 포함 토글
 *  - 테이블: 이름 / 이메일 / 가입 / 마지막 로그인 / 상태 / 제어
 *  - 페이지네이션 (페이지 크기 20 고정)
 */

import * as React from "react";
import { Search, UserCheck, UserX, Users } from "lucide-react";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminPagination,
  AdminTableSkeleton,
} from "@/features/admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAdminUsers, useSetUserActive } from "@/hooks/useAdmin";
import { useToast } from "@/providers/ToastProvider";
import type { ApiError } from "@/types";

export default function AdminUsersPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <UsersContent />
      </AdminShell>
    </AdminGuard>
  );
}

function UsersContent() {
  const toast = useToast();
  const [keywordInput, setKeywordInput] = React.useState("");
  const [keyword, setKeyword] = React.useState("");
  const [includeInactive, setIncludeInactive] = React.useState(false);
  const [page, setPage] = React.useState(1);

  // Debounce 검색
  React.useEffect(() => {
    const t = setTimeout(() => {
      setKeyword(keywordInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [keywordInput]);

  const { data, isLoading, isError, error, refetch } = useAdminUsers({
    page,
    size: 20,
    search_keyword: keyword || undefined,
    include_inactive_users: includeInactive,
  });

  const { mutate: setActive, isPending } = useSetUserActive();

  const users = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const handleToggle = (userId: string, nextActive: boolean) => {
    setActive(
      { userId, isActive: nextActive },
      {
        onSuccess: () => {
          toast.success(
            nextActive ? "계정이 활성화되었습니다." : "계정이 비활성화되었습니다."
          );
        },
        onError: (err) => {
          toast.error("변경 실패", { message: (err as unknown as ApiError).message });
        },
      }
    );
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-ink">유저 관리</h2>
        <p className="mt-0.5 text-sm text-ink-secondary">
          가입한 사장님 계정을 조회·검색하고 상태를 관리합니다.
        </p>
      </div>

      {/* 필터 바 */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
          <div className="flex-1">
            <Input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              placeholder="이름 · 이메일 · 사업자번호로 검색"
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
          <label className="flex items-center gap-2 whitespace-nowrap">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => {
                setIncludeInactive(e.target.checked);
                setPage(1);
              }}
              className="h-4 w-4 rounded border-surface-border text-primary-600 focus:ring-primary-500"
            />
            <Label className="mb-0 cursor-pointer text-sm">
              비활성 계정 포함
            </Label>
          </label>
          <span className="text-xs text-ink-tertiary numeric">
            {totalCount.toLocaleString()}명
          </span>
        </CardContent>
      </Card>

      {/* 테이블 */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6">
              <AdminTableSkeleton rows={8} />
            </div>
          ) : isError ? (
            <div className="p-6">
              <AdminErrorState
                message={(error as unknown as ApiError)?.message}
                onRetry={() => refetch()}
              />
            </div>
          ) : users.length === 0 ? (
            <AdminEmptyState
              icon={Users}
              title={
                keyword
                  ? `"${keyword}" 검색 결과가 없습니다`
                  : "등록된 유저가 없습니다"
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-muted text-xs font-semibold uppercase text-ink-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left">이름</th>
                    <th className="px-4 py-3 text-left">이메일</th>
                    <th className="px-4 py-3 text-left">공급자</th>
                    <th className="px-4 py-3 text-right">사업장</th>
                    <th className="px-4 py-3 text-left">가입일</th>
                    <th className="px-4 py-3 text-left">최근 로그인</th>
                    <th className="px-4 py-3 text-left">상태</th>
                    <th className="px-4 py-3 text-right">관리</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {users.map((u) => (
                    <tr key={u.user_id} className="hover:bg-surface-muted/50">
                      <td className="px-4 py-3 font-medium text-ink">
                        {u.name}
                      </td>
                      <td className="px-4 py-3 text-ink-secondary">
                        {u.email}
                      </td>
                      <td className="px-4 py-3 text-ink-secondary">
                        {u.provider ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right numeric text-ink-secondary">
                        {u.biz_count ?? 0}
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-tertiary">
                        {new Date(u.created_at).toLocaleDateString("ko-KR")}
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-tertiary">
                        {u.last_login_at
                          ? new Date(u.last_login_at).toLocaleString("ko-KR")
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={
                            u.is_active
                              ? "success"
                              : u.status === "SUSPENDED"
                                ? "danger"
                                : "default"
                          }
                        >
                          {u.is_active
                            ? "활성"
                            : u.status === "SUSPENDED"
                              ? "정지"
                              : "비활성"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant={u.is_active ? "secondary" : "primary"}
                          disabled={isPending}
                          onClick={() => handleToggle(u.user_id, !u.is_active)}
                        >
                          {u.is_active ? (
                            <>
                              <UserX className="h-3.5 w-3.5" />
                              비활성화
                            </>
                          ) : (
                            <>
                              <UserCheck className="h-3.5 w-3.5" />
                              활성화
                            </>
                          )}
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
    </div>
  );
}
