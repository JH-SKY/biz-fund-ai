"use client";

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
import { TestLoginCard } from "@/features/auth/TestLoginCard";

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
    <div className="w-full max-w-md space-y-4">
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

      <TestLoginCard redirectTo={redirectTo} onError={setError} />
    </div>
  );
}
