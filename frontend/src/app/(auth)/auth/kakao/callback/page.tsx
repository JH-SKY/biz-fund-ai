"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { Route } from "next";

import { authService } from "@/lib/services";
import { useAuthStore } from "@/stores/auth-store";

const KAKAO_REDIRECT_URI = process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI ?? "";

type CallbackStatus = "loading" | "error";

const ERROR_MESSAGES: Record<string, string> = {
  access_denied: "카카오 로그인이 취소되었습니다.",
  token_exchange_failed: "카카오 토큰 교환에 실패했습니다. 다시 시도해 주세요.",
  unknown: "로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.",
};

export default function KakaoCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((state) => state.login);

  const [status, setStatus] = useState<CallbackStatus>("loading");
  const [errorKey, setErrorKey] = useState<string>("unknown");
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;
    processedRef.current = true;

    const code = searchParams.get("code");
    const error = searchParams.get("error");

    if (error === "access_denied" || !code) {
      setErrorKey(error === "access_denied" ? "access_denied" : "unknown");
      setStatus("error");
      return;
    }

    authService
      .kakaoCallback({ code, redirect_uri: KAKAO_REDIRECT_URI })
      .then((data) => {
        login(
          { access: data.access_token, refresh: data.refresh_token },
          {
            userId: data.user_id,
            name: data.name,
            provider: "kakao",
            isOnboarded: !data.is_new_user,
          }
        );

        const savedRedirect = sessionStorage.getItem("kakao_oauth_redirect");
        sessionStorage.removeItem("kakao_oauth_redirect");

        const destination = data.is_new_user
          ? "/onboarding"
          : (savedRedirect ?? "/dashboard");

        router.replace(destination as Route);
      })
      .catch(() => {
        setErrorKey("token_exchange_failed");
        setStatus("error");
      });
  }, [searchParams, login, router]);

  if (status === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100">
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#ef4444"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <p className="text-base font-semibold text-gray-800">
            {ERROR_MESSAGES[errorKey] ?? ERROR_MESSAGES.unknown}
          </p>
        </div>
        <button
          type="button"
          onClick={() => router.replace("/login" as Route)}
          className="rounded-lg bg-[#FEE500] px-6 py-2.5 text-sm font-semibold text-[#191919] hover:bg-[#FDD835] transition-colors"
        >
          로그인 페이지로 돌아가기
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <div className="flex flex-col items-center gap-3">
        <svg
          width="36"
          height="36"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden
          className="animate-spin text-[#FEE500]"
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
        <p className="text-sm text-gray-500">카카오 로그인을 처리하고 있습니다...</p>
      </div>
    </div>
  );
}
