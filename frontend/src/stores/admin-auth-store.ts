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

  readonly isAdminAuthenticated: boolean;

  loginAdmin: (token: string, profile: AdminProfile) => void;
  logoutAdmin: () => void;
  setAdminToken: (token: string) => void;
  patchAdmin: (partial: Partial<AdminProfile>) => void;
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

      get isAdminAuthenticated() {
        return Boolean(get().adminToken);
      },

      loginAdmin(token, profile) {
        set({ adminToken: token, admin: profile });
      },

      logoutAdmin() {
        set({ adminToken: null, admin: null });
      },

      setAdminToken(token) {
        set({ adminToken: token });
      },

      patchAdmin(partial) {
        set((s) => ({
          admin: s.admin ? { ...s.admin, ...partial } : s.admin,
        }));
      },
    }),
    {
      name: "biz_up_admin_auth",
      storage: createJSONStorage(safeStorage),
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
