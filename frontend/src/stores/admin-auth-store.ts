/**
 * 관리자(Admin) 인증 전역 스토어.
 *
 * 책임
 *  - adminToken 보관 (persist → localStorage, key: "biz_up_admin_auth")
 *  - 로그인한 관리자 프로필(adminId, name, role)
 *  - loginAdmin / logoutAdmin / setAdminToken 액션
 *
 * 일반 유저용 auth-store 와 완전히 분리되어야 한다.
 *  - 서로 다른 localStorage key 사용
 *  - admin-api-client.ts 에서 adminToken 만 참조
 *  - 유저 logout 이 어드민 세션에 영향을 주지 않음
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface AdminProfile {
  adminId: string;
  name: string;
  role: "SUPER_ADMIN" | "OPERATOR" | string;
  expiresAt?: string | null;
}

interface AdminAuthState {
  adminToken: string | null;
  admin: AdminProfile | null;
  hasHydrated: boolean;

  readonly isAdminAuthenticated: boolean;

  loginAdmin: (token: string, profile: AdminProfile) => void;
  logoutAdmin: () => void;
  setAdminToken: (token: string) => void;
  patchAdmin: (partial: Partial<AdminProfile>) => void;
  setHasHydrated: (value: boolean) => void;
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

export const useAdminAuthStore = create<AdminAuthState>()(
  persist(
    (set, get) => ({
      adminToken: null,
      admin: null,
      hasHydrated: false,

      get isAdminAuthenticated() {
        return Boolean(get().adminToken);
      },

      loginAdmin(token, profile) {
        set({ adminToken: token, admin: profile, hasHydrated: true });
      },

      logoutAdmin() {
        set({ adminToken: null, admin: null, hasHydrated: true });
      },

      setAdminToken(token) {
        set({ adminToken: token, hasHydrated: true });
      },

      patchAdmin(partial) {
        set((s) => ({
          admin: s.admin ? { ...s.admin, ...partial } : s.admin,
        }));
      },

      setHasHydrated(value) {
        set({ hasHydrated: value });
      },
    }),
    {
      name: "biz_up_admin_auth",
      storage: createJSONStorage(safeStorage),
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          // 파싱 오류 등 — 토큰을 무효화하고 반드시 hydrated 처리
          if (state) {
            state.logoutAdmin(); // logoutAdmin 내부에서 hasHydrated: true 설정
          } else {
            // state가 undefined인 극단적 케이스: 직접 스토어 상태 갱신
            useAdminAuthStore.getState().setHasHydrated(true);
          }
          return;
        }
        if (state) {
          state.setHasHydrated(true);
        } else {
          useAdminAuthStore.getState().setHasHydrated(true);
        }
      },
    }
  )
);

/** React 외부(axios 인터셉터 등) 에서 토큰 읽기용 헬퍼 */
export function getAdminTokenNonReactive(): string | null {
  return useAdminAuthStore.getState().adminToken;
}

export function clearAdminAuthNonReactive(): void {
  useAdminAuthStore.getState().logoutAdmin();
}
