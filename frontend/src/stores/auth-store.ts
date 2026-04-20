/**
 * 인증(Auth) 전역 스토어.
 *
 * 책임
 *  - accessToken / refreshToken 보관 (persist → localStorage)
 *  - 로그인한 유저 프로필 (id, name, provider, isOnboarded)
 *  - login / logout / setTokens / setOnboarded 액션
 *
 * api-client.ts 와의 연동
 *  - getAccessTokenNonReactive() : axios 인터셉터에서 React 외부로 토큰 읽기
 *  - getRefreshTokenNonReactive(): 토큰 재발급 시 refresh_token 읽기
 *
 * business-store 와의 관계
 *  - logout() 에서 business-store.clear() 도 함께 호출해 전체 상태 초기화
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// ── 타입 ──────────────────────────────────────────────────────────────
export type SocialProvider = "kakao" | "naver";

export interface AuthUser {
  /** 백엔드 users.id (UUID) */
  userId: string;
  /** 소셜 플랫폼에서 받은 표시 이름 */
  name?: string | null;
  provider: SocialProvider;
  /** 온보딩 완료 여부 (DB 플래그 `is_onboarded`) */
  isOnboarded: boolean;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;

  // ── 파생 상태 ──────────────────────────────────────────────────────
  /** accessToken 이 존재하면 로그인된 것으로 간주 */
  readonly isAuthenticated: boolean;

  // ── 액션 ───────────────────────────────────────────────────────────
  /** 소셜 로그인 성공 직후: 토큰 + 유저 정보 저장 */
  login: (tokens: { access: string; refresh: string }, user: AuthUser) => void;
  /** 로그아웃: 스토어 + localStorage 전부 초기화 */
  logout: () => void;
  /** 토큰만 갱신 (silent refresh) */
  setTokens: (access: string, refresh?: string) => void;
  /** 온보딩 완료 플래그 갱신 */
  setOnboarded: () => void;
  /** 유저 이름 등 프로필 부분 갱신 */
  patchUser: (partial: Partial<AuthUser>) => void;
}

// ── SSR 안전 스토리지 ──────────────────────────────────────────────────
function safeStorage() {
  if (typeof window === "undefined") {
    return {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
    };
  }
  return window.localStorage;
}

// ── Store ──────────────────────────────────────────────────────────────
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      get isAuthenticated() {
        return Boolean(get().accessToken);
      },

      login({ access, refresh }, user) {
        set({ accessToken: access, refreshToken: refresh, user });
      },

      logout() {
        set({ accessToken: null, refreshToken: null, user: null });
        // business-store 도 함께 초기화 (순환 의존 방지를 위해 dynamic import)
        import("@/stores/business-store").then(({ useBusinessStore }) => {
          useBusinessStore.getState().clear();
        });
      },

      setTokens(access, refresh) {
        set((s) => ({
          accessToken: access,
          refreshToken: refresh ?? s.refreshToken,
        }));
      },

      setOnboarded() {
        set((s) => ({
          user: s.user ? { ...s.user, isOnboarded: true } : s.user,
        }));
      },

      patchUser(partial) {
        set((s) => ({
          user: s.user ? { ...s.user, ...partial } : s.user,
        }));
      },
    }),
    {
      name: "biz_up_auth",
      storage: createJSONStorage(safeStorage),
      // 토큰은 민감 정보 — user 프로필만 선별 직렬화하고 싶다면 partialize 사용 가능.
      // 현재는 전체를 그대로 저장.
    }
  )
);

// ── React 외부(axios 인터셉터 등) 에서 토큰 읽기용 헬퍼 ───────────────
export function getAccessTokenNonReactive(): string | null {
  return useAuthStore.getState().accessToken;
}

export function getRefreshTokenNonReactive(): string | null {
  return useAuthStore.getState().refreshToken;
}
