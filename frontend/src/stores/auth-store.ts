/**
 * 인증(Auth) 전역 스토어
 *
 * 책임
 *  - accessToken / refreshToken 보관 (persist -> localStorage)
 *  - 로그인 유저 정보(userId, name, provider, isOnboarded) 관리
 *  - hydration 완료 여부 관리
 *  - login / logout / setTokens / setOnboarded 액션 제공
 */

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type SocialProvider = "kakao" | "naver";

export interface AuthUser {
  userId: string;
  name?: string | null;
  provider: SocialProvider;
  isOnboarded: boolean;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  hasHydrated: boolean;

  readonly isAuthenticated: boolean;

  login: (tokens: { access: string; refresh: string }, user: AuthUser) => void;
  logout: () => void;
  setTokens: (access: string, refresh?: string) => void;
  setHasHydrated: (value: boolean) => void;
  setOnboarded: () => void;
  patchUser: (partial: Partial<AuthUser>) => void;
}

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

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      hasHydrated: false,

      get isAuthenticated() {
        return Boolean(get().accessToken);
      },

      login({ access, refresh }, user) {
        set({
          accessToken: access,
          refreshToken: refresh,
          user,
          hasHydrated: true,
        });
      },

      logout() {
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          hasHydrated: true,
        });
        import("@/stores/business-store").then(({ useBusinessStore }) => {
          useBusinessStore.getState().clear();
        });
      },

      setTokens(access, refresh) {
        set((state) => ({
          accessToken: access,
          refreshToken: refresh ?? state.refreshToken,
          hasHydrated: true,
        }));
      },

      setHasHydrated(value) {
        set({ hasHydrated: value });
      },

      setOnboarded() {
        set((state) => ({
          user: state.user ? { ...state.user, isOnboarded: true } : state.user,
        }));
      },

      patchUser(partial) {
        set((state) => ({
          user: state.user ? { ...state.user, ...partial } : state.user,
        }));
      },
    }),
    {
      name: "biz_up_auth",
      storage: createJSONStorage(safeStorage),
      // hasHydrated 는 런타임 전용 플래그 — localStorage 에 저장하면 안 됨.
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
      // 에러가 있어도 토큰을 지우지 않는다: 토큰 유효성은 API 가 판단.
      // state 가 undefined 인 경우 → Guard 의 타임아웃 안전장치가 대응.
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

export function getAccessTokenNonReactive(): string | null {
  return useAuthStore.getState().accessToken;
}

export function getRefreshTokenNonReactive(): string | null {
  return useAuthStore.getState().refreshToken;
}
