"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Route } from "next";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/lib/services";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import type { SocialProvider } from "@/types";

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
  const login = useAuthStore((state) => state.login);

  const [loading, setLoading] = useState<SocialProvider | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [socialAccessToken, setSocialAccessToken] = useState("");

  // ── 카카오: 기존 토큰 입력 방식 유지 ──────────────────────
  const openKakaoDialog = () => {
    setSocialAccessToken("");
    setDialogOpen(true);
  };

  const handleKakaoLogin = async () => {
    const trimmedToken = socialAccessToken.trim();
    if (!trimmedToken) {
      onError?.("카카오 액세스 토큰을 입력해 주세요.");
      return;
    }

    setLoading("KAKAO");
    try {
      const data = await authService.socialLogin({
        access_token: trimmedToken,
        provider: "KAKAO",
        device_type: "WEB",
      });

      login(
        { access: data.access_token, refresh: data.refresh_token },
        {
          userId: data.user_id,
          name: data.name,
          provider: "kakao",
          isOnboarded: !data.is_new_user,
        }
      );

      setDialogOpen(false);
      router.push((data.is_new_user ? "/onboarding" : redirectTo) as Route);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "카카오 로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.";
      onError?.(message);
    } finally {
      setLoading(null);
    }
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

    // URLSearchParams는 값을 자동 인코딩하므로 redirect_uri만 수동 조립
    const query = [
      "response_type=code",
      `client_id=${encodeURIComponent(NAVER_CLIENT_ID)}`,
      `redirect_uri=${encodeURIComponent(NAVER_REDIRECT_URI)}`,
      `state=${encodeURIComponent(state)}`,
    ].join("&");

    window.location.href = `https://nid.naver.com/oauth2.0/authorize?${query}`;
  };

  return (
    <>
      <div className="flex flex-col gap-3">
        <button
          type="button"
          onClick={openKakaoDialog}
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

      {/* 카카오 액세스 토큰 입력 다이얼로그 */}
      <Dialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="카카오 액세스 토큰 입력"
        description="카카오에서 발급받은 액세스 토큰을 입력하면 백엔드 /auth/social-login 으로 전달해 로그인합니다."
        footer={
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setDialogOpen(false)}
            >
              취소
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={handleKakaoLogin}
              loading={loading === "KAKAO"}
            >
              로그인
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="social-access-token" required>
              카카오 액세스 토큰
            </Label>
            <Input
              id="social-access-token"
              value={socialAccessToken}
              onChange={(event) => setSocialAccessToken(event.target.value)}
              placeholder="발급받은 액세스 토큰을 입력해 주세요"
            />
          </div>
          <p className="text-xs text-ink-secondary">
            로그인 성공 시 신규 사용자는 온보딩으로, 기존 사용자는 원래 가려던
            페이지로 이동합니다.
          </p>
        </div>
      </Dialog>
    </>
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
