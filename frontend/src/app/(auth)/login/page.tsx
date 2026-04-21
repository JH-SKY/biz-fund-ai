"use client";

/**
 * [P02] 로그인 / 회원가입 페이지 — `/login`
 *
 * - 이메일·비밀번호 입력 없이 소셜 로그인(카카오·네이버) 단일화
 * - 실패 시 인라인 에러 메시지 노출 (토스트 컴포넌트 도입 전 임시)
 * - 성공 후 분기: 신규 유저 → /onboarding / 기존 유저 → /dashboard (백엔드 응답 기준)
 */

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, ShieldCheck } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SocialLoginButtons } from "@/features/auth/SocialLoginButtons";

export default function LoginPage() {
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const redirectTo = useMemo(() => {
    const raw = searchParams.get("callbackUrl");
    if (!raw || !raw.startsWith("/")) {
      return "/dashboard";
    }
    return raw;
  }, [searchParams]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">사장님, 어서오세요!</CardTitle>
        <CardDescription>
          정책자금 진단 · 비즈픽 · AI 상담 모두 무료로 시작하세요.
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
          에 동의한 것으로 간주됩니다.
        </p>
      </CardContent>
    </Card>
  );
}
