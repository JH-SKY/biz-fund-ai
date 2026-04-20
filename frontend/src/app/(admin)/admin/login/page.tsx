"use client";

/**
 * /admin/login — 관리자 로그인 페이지.
 *
 * 일반 사용자 소셜 로그인과 달리 ID/PW 직접 입력 방식.
 * 성공 시 adminToken 을 admin-auth-store 에 저장 후 /admin/dashboard 로 이동.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Lock, User, Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AdminPublicGuard } from "@/components/admin";
import { useAdminAuthStore } from "@/stores/admin-auth-store";
import { useAdminLogin } from "@/hooks/useAdmin";
import { useToast } from "@/providers/ToastProvider";
import type { ApiError } from "@/types";

export default function AdminLoginPage() {
  return (
    <AdminPublicGuard>
      <AdminLoginForm />
    </AdminPublicGuard>
  );
}

function AdminLoginForm() {
  const router = useRouter();
  const toast = useToast();
  const loginAdmin = useAdminAuthStore((s) => s.loginAdmin);
  const { mutate, isPending } = useAdminLogin();

  const [loginId, setLoginId] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [showPw, setShowPw] = React.useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginId.trim() || !password) {
      toast.warning("아이디와 비밀번호를 모두 입력해주세요.");
      return;
    }
    mutate(
      { login_id: loginId.trim(), password },
      {
        onSuccess: (res) => {
          loginAdmin(res.admin_token, {
            adminId: res.admin_id,
            name: res.name,
            role: res.role,
            expiresAt: res.expires_at ?? null,
          });
          toast.success("환영합니다", {
            message: `${res.name} 관리자님, 로그인되었습니다.`,
          });
          router.replace("/admin/dashboard");
        },
        onError: (err) => {
          const apiError = err as unknown as ApiError;
          toast.error("로그인 실패", {
            message:
              apiError.status === 401 || apiError.status === 403
                ? "아이디 또는 비밀번호가 올바르지 않습니다."
                : apiError.message,
          });
        },
      }
    );
  };

  return (
    <div className="min-h-dvh bg-gradient-to-br from-ink via-primary-950 to-primary-900 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-600 text-white shadow-elevated">
            <ShieldCheck className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-bold text-white">Biz-Up Admin</h1>
          <p className="mt-1 text-sm text-white/60">
            통합 관리 센터 접근을 위해 관리자 인증이 필요합니다.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl bg-white p-6 shadow-elevated space-y-5"
        >
          <div className="space-y-2">
            <Label htmlFor="admin-login-id">관리자 아이디</Label>
            <Input
              id="admin-login-id"
              type="text"
              autoComplete="username"
              placeholder="admin@bizup.kr"
              value={loginId}
              onChange={(e) => setLoginId(e.target.value)}
              leftIcon={<User className="h-4 w-4" />}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="admin-password">비밀번호</Label>
            <Input
              id="admin-password"
              type={showPw ? "text" : "password"}
              autoComplete="current-password"
              placeholder="********"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock className="h-4 w-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  aria-label={showPw ? "비밀번호 숨기기" : "비밀번호 표시"}
                  className="text-ink-tertiary hover:text-ink"
                >
                  {showPw ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              }
              required
            />
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full"
            loading={isPending}
            disabled={isPending}
          >
            {isPending ? "확인 중..." : "로그인"}
          </Button>

          <p className="rounded-lg bg-primary-50 p-3 text-[11px] leading-relaxed text-primary-700">
            ⚠️ 이 페이지는 내부 운영자 전용입니다. 모든 접근 기록은 감사 로그에
            남습니다. 자격이 없는 접근은 법적 책임을 질 수 있습니다.
          </p>
        </form>
      </div>
    </div>
  );
}
