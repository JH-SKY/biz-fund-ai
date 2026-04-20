"use client";

/**
 * SocialLoginButtons — 카카오 / 네이버 간편 로그인.
 *
 * 브랜드 컬러
 *  - 카카오: #FEE500 + 검정 텍스트
 *  - 네이버: #03C75A + 흰 텍스트
 *
 * 구현 상태
 *  - 실제 OAuth 플로우는 백엔드 /auth/social-login 엔드포인트가 통합 처리하므로,
 *    현재는 로직 골격만 구성하고 onClick 핸들러만 시뮬레이션한다.
 *  - TODO: window.location.href = `${OAUTH_KAKAO_URL}?redirect=/auth/callback?provider=KAKAO` 로 교체
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { SocialProvider } from "@/types";

interface SocialLoginButtonsProps {
  /** 로그인 성공 후 돌아갈 경로 (기본: /dashboard) */
  redirectTo?: string;
  onError?: (message: string) => void;
}

export function SocialLoginButtons({
  redirectTo = "/dashboard",
  onError,
}: SocialLoginButtonsProps) {
  const router = useRouter();
  const [loading, setLoading] = useState<SocialProvider | null>(null);

  const handleLogin = async (provider: SocialProvider) => {
    setLoading(provider);
    try {
      // TODO: 실제 OAuth 리다이렉트로 교체
      // window.location.href = `/auth/oauth?provider=${provider}&next=${redirectTo}`;
      //
      // 임시 시뮬레이션:
      // - 신규 유저라 가정하여 /onboarding 으로 이동
      // - 기존 유저라면 redirectTo 로 이동하도록 백엔드 응답에 따라 분기
      await new Promise((r) => setTimeout(r, 600));
      router.push("/onboarding");
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "로그인에 실패했습니다. 다시 시도해주세요.";
      onError?.(msg);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        onClick={() => handleLogin("KAKAO")}
        disabled={loading !== null}
        aria-label="카카오로 시작하기"
        className={cn(
          "flex h-12 items-center justify-center gap-2 rounded-lg font-semibold",
          "bg-[#FEE500] text-[#191919] hover:bg-[#FDD835]",
          "transition-colors disabled:opacity-60"
        )}
      >
        <KakaoIcon />
        {loading === "KAKAO" ? "로그인 중..." : "카카오로 시작하기"}
      </button>

      <button
        type="button"
        onClick={() => handleLogin("NAVER")}
        disabled={loading !== null}
        aria-label="네이버로 시작하기"
        className={cn(
          "flex h-12 items-center justify-center gap-2 rounded-lg font-semibold",
          "bg-[#03C75A] text-white hover:bg-[#029B47]",
          "transition-colors disabled:opacity-60"
        )}
      >
        <NaverIcon />
        {loading === "NAVER" ? "로그인 중..." : "네이버로 시작하기"}
      </button>
    </div>
  );
}

function KakaoIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <path d="M12 3C6.48 3 2 6.6 2 11.04c0 2.85 1.86 5.34 4.66 6.77-.2.74-.72 2.7-.82 3.12-.12.53.2.52.4.37.16-.11 2.56-1.74 3.6-2.44.71.1 1.43.16 2.16.16 5.52 0 10-3.6 10-8.04S17.52 3 12 3z" />
    </svg>
  );
}

function NaverIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <path d="M16.5 3.5v9.4L7.5 3.5H3.5v17h4V11l9 9.5h4v-17z" />
    </svg>
  );
}
