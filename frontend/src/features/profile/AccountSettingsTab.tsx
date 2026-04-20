"use client";

/**
 * 계정 설정 탭 — 소셜 연결 상태, 알림 수신 설정, 회원탈퇴.
 */

import * as React from "react";
import { LogOut, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import {
  useNotificationSettings,
  useUpdateNotificationSettings,
  useDeleteAccount,
} from "@/hooks/useProfile";
import { useAuthStore } from "@/stores/auth-store";
import type { NotificationSettings } from "@/types";

interface ToggleRowProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
  disabled,
}: ToggleRowProps) {
  const id = React.useId();
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="space-y-0.5">
        <label htmlFor={id} className="cursor-pointer text-sm font-medium text-ink">
          {label}
        </label>
        {description && (
          <p className="text-xs text-ink-secondary">{description}</p>
        )}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
          "disabled:pointer-events-none disabled:opacity-50",
          checked ? "bg-primary-600" : "bg-surface-border",
        ].join(" ")}
      >
        <span
          className={[
            "pointer-events-none inline-block h-5 w-5 translate-y-0.5 rounded-full bg-white shadow-sm transition-transform",
            checked ? "translate-x-5" : "translate-x-0.5",
          ].join(" ")}
        />
      </button>
    </div>
  );
}

export function AccountSettingsTab() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const { data: settings, isLoading } = useNotificationSettings();
  const updateSettings = useUpdateNotificationSettings();
  const deleteAccount = useDeleteAccount();

  const [confirmDelete, setConfirmDelete] = React.useState(false);

  async function handleToggle(
    key: keyof NotificationSettings,
    value: boolean
  ) {
    await updateSettings.mutateAsync({ [key]: value });
  }

  async function handleDeleteAccount() {
    await deleteAccount.mutateAsync();
    logout();
  }

  const providerLabel = user?.provider === "kakao" ? "카카오" : "네이버";

  return (
    <div className="space-y-6">
      {/* 소셜 연결 상태 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">소셜 계정 연결</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between rounded-lg border border-surface-border bg-surface-subtle px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">
                {user?.provider === "kakao" ? "🟡" : "🟢"}
              </span>
              <div>
                <p className="text-sm font-medium text-ink">
                  {providerLabel} 로그인 연결됨
                </p>
                <p className="text-xs text-ink-secondary">
                  {user?.name ?? "사용자"}
                </p>
              </div>
            </div>
            <span className="rounded-full bg-success-50 px-3 py-1 text-xs font-semibold text-success-600">
              연결됨
            </span>
          </div>
        </CardContent>
      </Card>

      {/* 알림 설정 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">알림 수신 설정</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="h-12 animate-pulse rounded-lg bg-surface-subtle"
                />
              ))}
            </div>
          ) : settings ? (
            <div className="divide-y divide-surface-border">
              <ToggleRow
                label="전체 푸시 알림"
                description="모든 알림을 켜거나 끕니다"
                checked={settings.push_enabled}
                onChange={(v) => handleToggle("push_enabled", v)}
                disabled={updateSettings.isPending}
              />
              <ToggleRow
                label="정책 업데이트 알림"
                description="마감임박, 신규 정책 매칭 등"
                checked={settings.policy_update_enabled}
                onChange={(v) => handleToggle("policy_update_enabled", v)}
                disabled={updateSettings.isPending || !settings.push_enabled}
              />
              <ToggleRow
                label="AI 상담 답변 알림"
                description="비즈몽 답변 완료 시 알림"
                checked={settings.chat_answer_enabled}
                onChange={(v) => handleToggle("chat_answer_enabled", v)}
                disabled={updateSettings.isPending || !settings.push_enabled}
              />
              <ToggleRow
                label="마케팅 알림"
                description="이벤트, 프로모션 정보"
                checked={settings.marketing_enabled}
                onChange={(v) => handleToggle("marketing_enabled", v)}
                disabled={updateSettings.isPending || !settings.push_enabled}
              />
            </div>
          ) : (
            <p className="text-sm text-ink-secondary">
              알림 설정을 불러올 수 없습니다.
            </p>
          )}
        </CardContent>
      </Card>

      {/* 로그아웃 + 회원탈퇴 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-ink-secondary">
            계정 관리
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            variant="secondary"
            className="w-full gap-2"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" />
            로그아웃
          </Button>
          <Button
            variant="destructive"
            className="w-full gap-2"
            onClick={() => setConfirmDelete(true)}
          >
            <Trash2 className="h-4 w-4" />
            회원탈퇴
          </Button>
        </CardContent>
      </Card>

      <Dialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="정말 탈퇴하시겠어요?"
        description="탈퇴 시 모든 사업장 정보·진단 이력·서류가 삭제되며 복구할 수 없습니다."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              취소
            </Button>
            <Button
              variant="destructive"
              loading={deleteAccount.isPending}
              onClick={handleDeleteAccount}
            >
              탈퇴하기
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-secondary">
          서비스 이용 데이터가 모두 삭제되며, 이 작업은 취소할 수 없습니다.
          신중하게 결정해 주세요.
        </p>
      </Dialog>
    </div>
  );
}
