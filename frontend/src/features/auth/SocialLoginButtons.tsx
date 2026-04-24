"use client";

import { cn } from "@/lib/utils";

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
