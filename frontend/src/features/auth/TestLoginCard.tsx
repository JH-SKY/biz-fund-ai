"use client";

import type { Route } from "next";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FlaskConical, KeyRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/lib/services";
import { useAuthStore } from "@/stores/auth-store";

interface TestLoginCardProps {
  redirectTo?: string;
  onError?: (message: string) => void;
}

const TEST_LOGIN_ENABLED =
  process.env.NEXT_PUBLIC_ENABLE_TEST_LOGIN === "true" ||
  process.env.NODE_ENV !== "production";

export function TestLoginCard({
  redirectTo = "/dashboard",
  onError,
}: TestLoginCardProps) {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);

  const [testUserKey, setTestUserKey] = useState("demo-owner");
  const [loading, setLoading] = useState(false);

  if (!TEST_LOGIN_ENABLED) {
    return null;
  }

  const handleTestLogin = async () => {
    const trimmedKey = testUserKey.trim();
    if (!trimmedKey) {
      onError?.("테스트 로그인 키를 입력해 주세요.");
      return;
    }

    setLoading(true);
    try {
      const data = await authService.testLogin({ test_user_key: trimmedKey });

      login(
        {
          access: data.access_token,
          refresh: data.refresh_token,
        },
        {
          userId: data.user_id,
          provider: "kakao",
          isOnboarded: !data.is_new_user,
          name: trimmedKey,
        }
      );

      router.push((data.is_new_user ? "/onboarding" : redirectTo) as Route);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "테스트 계정 로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.";
      onError?.(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-dashed border-primary-200 bg-primary-50/50">
      <CardHeader className="space-y-2 pb-4">
        <div className="flex items-center gap-2 text-primary-700">
          <FlaskConical className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-[0.2em]">
            Pre-Deploy Access
          </span>
        </div>
        <CardTitle className="text-base text-ink">테스트 계정으로 바로 로그인</CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="test-user-key" required>
            테스트 로그인 키
          </Label>
          <Input
            id="test-user-key"
            value={testUserKey}
            onChange={(event) => setTestUserKey(event.target.value)}
            placeholder="예: demo-owner"
            leftIcon={<KeyRound className="h-4 w-4" />}
          />
        </div>

        <p className="text-xs text-ink-secondary">
          소셜 로그인 없이 바로 토큰을 발급받아 내부 시연과 전체 기능 점검에 사용할 수 있습니다.
        </p>
        <p className="text-xs text-ink-tertiary">
          예시 키: &quot;demo-owner&quot;, &quot;alice&quot;, &quot;bob&quot;,
          &quot;admin_tester&quot;
        </p>

        <Button
          type="button"
          className="w-full"
          loading={loading}
          onClick={handleTestLogin}
        >
          테스트 계정으로 로그인
        </Button>
      </CardContent>
    </Card>
  );
}
