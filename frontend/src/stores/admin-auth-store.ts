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
      // hasHydrated 는 런타임 전용 플래그 — localStorage 에 저장하면 안 됨.
      // 저장하면 다음 로드 시 병합된 값이 true 가 되어 onRehydrateStorage 가
      // 실행되기도 전에 가드가 인증 완료로 착각하는 문제가 생긴다.
      partialize: (state) => ({
        adminToken: state.adminToken,
        admin: state.admin,
      }),
      // onRehydrateStorage 는 최대한 단순하게 유지한다.
      // - state 가 undefined(극단적 에러)인 경우 → Guard 의 3초 타임아웃이 대응
      // - 에러가 있어도 토큰을 지우지 않는다: 토큰 유효성은 API 가 판단
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
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
