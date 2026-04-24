"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Route } from "next";

import { cn } from "@/lib/utils";
import type { SocialProvider } from "@/types";

const KAKAO_CLIENT_ID = process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID ?? "";
const KAKAO_REDIRECT_URI = process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI ?? "";
const NAVER_CLIENT_ID = process.env.NEXT_PUBLIC_NAVER_CLIENT_ID ?? "";
const NAVER_REDIRECT_URI = process.env.NEXT_PUBLIC_NAVER_REDIRECT_URI ?? "";

interface SocialLoginButtonsProps {
  redirectTo?: string;
  onError?: (message: string) => void;
}

export function SocialLoginButtons({
  redirectTo = "/dashboard",
  onError,
}: SocialLoginButtonsProps) {
  const router = useRouter();
  const [loading, setLoading] = useState<SocialProvider | null>(null);

  // ── 카카오: OAuth 인가 코드 플로우 ────────────────────────
  const handleKakaoLogin = () => {
    if (!KAKAO_CLIENT_ID || !KAKAO_REDIRECT_URI) {
      onError?.("카카오 로그인 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.");
      return;
    }

    if (redirectTo !== "/dashboard") {
      sessionStorage.setItem("kakao_oauth_redirect", redirectTo);
    }

    const query = [
      "response_type=code",
      `client_id=${encodeURIComponent(KAKAO_CLIENT_ID)}`,
      `redirect_uri=${encodeURIComponent(KAKAO_REDIRECT_URI)}`,
    ].join("&");

    window.location.href = `https://kauth.kakao.com/oauth/authorize?${query}`;
  };

  // ── 네이버: OAuth 인가 코드 플로우 ────────────────────────
  const handleNaverLogin = () => {
    if (!NAVER_CLIENT_ID || !NAVER_REDIRECT_URI) {
      onError?.("네이버 로그인 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.");
      return;
    }

    const state = crypto.randomUUID();
    sessionStorage.setItem("naver_oauth_state", state);
    if (redirectTo !== "/dashboard") {
      sessionStorage.setItem("naver_oauth_redirect", redirectTo);
    }

    const query = [
      "response_type=code",
      `client_id=${encodeURIComponent(NAVER_CLIENT_ID)}`,
      `redirect_uri=${encodeURIComponent(NAVER_REDIRECT_URI)}`,
      `state=${encodeURIComponent(state)}`,
    ].join("&");

    window.location.href = `https://nid.naver.com/oauth2.0/authorize?${query}`;
  };

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        onClick={handleNaverLogin}
        disabled={loading !== null}
        aria-label="네이버로 시작하기"
        className={cn(
          "flex h-12 items-center justify-center gap-2 rounded-lg font-semibold",
          "bg-[#03C75A] text-white hover:bg-[#029B47]",
          "transition-colors disabled:opacity-60"
        )}
      >
        <NaverIcon />
        네이버로 시작하기
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
