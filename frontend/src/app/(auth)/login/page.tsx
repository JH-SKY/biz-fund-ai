"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ShieldCheck } from "lucide-react";
import type { Route } from "next";
import type { DevTestAccountItem } from "@/types";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SocialLoginButtons } from "@/features/auth/SocialLoginButtons";
import { authService } from "@/lib/services";
import { useAuthStore } from "@/stores/auth-store";

export default function LoginPage() {
  const isDevMode = process.env.NODE_ENV !== "production";
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((state) => state.login);

  const [error, setError] = useState<string | null>(null);
  const [naverLoading, setNaverLoading] = useState(false);
  const [devAccounts, setDevAccounts] = useState<DevTestAccountItem[]>([]);
  const [devLoadingKey, setDevLoadingKey] = useState<string | null>(null);
  const processedRef = useRef(false);

  const redirectTo = useMemo(() => {
    const raw = searchParams.get("callbackUrl");
    if (!raw || !raw.startsWith("/")) return "/dashboard";
    return raw;
  }, [searchParams]);

  // ── 네이버 OAuth 콜백 처리 ────────────────────────────
  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const naverError = searchParams.get("error");

    // 네이버 콜백 파라미터가 없으면 일반 로그인 페이지로 표시
    if (!code && !naverError) return;
    // 중복 실행 방지
    if (processedRef.current) return;
    processedRef.current = true;

    // 네이버 로그인 취소
    if (naverError === "access_denied") {
      setError("네이버 로그인이 취소되었습니다.");
      return;
    }

    if (!code || !state) {
      setError("네이버 로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.");
      return;
    }

    // state CSRF 검증
    const savedState = sessionStorage.getItem("naver_oauth_state");
    sessionStorage.removeItem("naver_oauth_state");

    if (!savedState || savedState !== state) {
      setError("보안 검증에 실패했습니다. 다시 로그인해 주세요.");
      return;
    }

    // 백엔드 토큰 교환
    setNaverLoading(true);
    authService
      .naverCallback({ code, state })
      .then((data) => {
        login(
          { access: data.access_token, refresh: data.refresh_token },
          {
            userId: data.user_id,
            name: data.name,
            provider: "naver",
            isOnboarded: !data.is_new_user,
          }
        );

        const savedRedirect = sessionStorage.getItem("naver_oauth_redirect");
        sessionStorage.removeItem("naver_oauth_redirect");

        const destination = data.is_new_user
          ? "/onboarding"
          : (savedRedirect ?? redirectTo);

        router.replace(destination as Route);
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error
            ? err.message
            : "네이버 로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.";
        setError(message);
        setNaverLoading(false);
      });
  }, [searchParams, login, router, redirectTo]);

  useEffect(() => {
    if (!isDevMode) return;

    authService
      .getDevTestAccounts()
      .then((accounts) => setDevAccounts(accounts))
      .catch(() => {
        setDevAccounts([]);
      });
  }, [isDevMode]);

  const handleDevLogin = (scenarioKey: string) => {
    setError(null);
    setDevLoadingKey(scenarioKey);

    authService
      .devLogin({ scenario_key: scenarioKey })
      .then((data) => {
        login(
          { access: data.access_token, refresh: data.refresh_token },
          {
            userId: data.user_id,
            name: data.name,
            provider: "naver",
            isOnboarded: !data.is_new_user,
          }
        );

        router.replace((data.is_new_user ? "/onboarding" : redirectTo) as Route);
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error
            ? err.message
            : "테스트 계정 로그인 중 오류가 발생했습니다. 다시 시도해 주세요.";
        setError(message);
      })
      .finally(() => {
        setDevLoadingKey(null);
      });
  };

  // 네이버 콜백 처리 중 로딩 화면
  if (naverLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <svg
          width="36"
          height="36"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden
          className="animate-spin text-[#03C75A]"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray="31.4 62.8"
          />
        </svg>
        <p className="text-sm text-gray-500">네이버 로그인을 처리하고 있습니다...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md space-y-4">
      {isDevMode && devAccounts.length > 0 && (
        <Card className="border-dashed border-amber-300 bg-amber-50/60">
          <CardHeader>
            <CardTitle className="text-lg">개발용 테스트 계정</CardTitle>
            <CardDescription>
              정책 매칭 시나리오를 바로 검증할 수 있도록 준비한 계정입니다.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {devAccounts.map((account) => (
              <div
                key={account.scenario_key}
                className="rounded-lg border border-amber-200 bg-white p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-ink-primary">
                      {account.display_name}
                    </p>
                    <p className="text-xs text-ink-secondary">
                      {account.business_name} · {account.email}
                    </p>
                    <p className="text-xs text-ink-secondary">{account.summary}</p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => handleDevLogin(account.scenario_key)}
                    disabled={devLoadingKey !== null}
                  >
                    {devLoadingKey === account.scenario_key ? "로그인 중..." : "바로 로그인"}
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">사장님, 어서오세요</CardTitle>
          <CardDescription>
            정책자금 진단과 비즈업 AI 상담 모두 무료로 시작하세요
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <SocialLoginButtons redirectTo={redirectTo} onError={setError} />

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg bg-danger-50 p-3 text-sm text-danger-600"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-start gap-2 rounded-lg border border-surface-border bg-surface-muted p-3 text-xs text-ink-secondary">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-success-600" />
            <p>
              카카오·네이버 계정으로 안전하게 로그인합니다. 비즈업은 비밀번호를
              직접 저장하지 않습니다.
            </p>
          </div>

          <p className="text-center text-xs text-ink-tertiary">
            로그인 시{" "}
            <a href="#" className="underline underline-offset-2 hover:text-ink-secondary">
              이용약관
            </a>
            {" 및 "}
            <a href="#" className="underline underline-offset-2 hover:text-ink-secondary">
              개인정보처리방침
            </a>
            에 동의한 것으로 간주합니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
