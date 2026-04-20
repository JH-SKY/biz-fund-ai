/**
 * 활성 사업장(bizId) 전역 스토어.
 *
 * 왜 필요한가
 *  - 백엔드 정책/진단 API 다수는 `X-Business-Id` 헤더를 요구 (backend/deps/policy_deps.py 참조).
 *  - 온보딩 직후 응답(`biz_id`)을 이 스토어에 저장하고, 이후 모든 API 호출에서
 *    axios 요청 인터셉터가 자동으로 헤더에 실어 보낸다.
 *
 * 영속화
 *  - localStorage 에 저장해 새로고침/재로그인해도 유지.
 *  - 로그아웃 시 `clear()` 필수.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface BusinessState {
  /** 활성 사업장 UUID. 온보딩 미완료 시 null. */
  activeBizId: string | null;
  /** 사장님 표시용 상호명 (UX 상 헤더/환영문구에 사용). */
  activeBizName: string | null;
  setActiveBusiness: (bizId: string, bizName?: string | null) => void;
  clear: () => void;
}

export const useBusinessStore = create<BusinessState>()(
  persist(
    (set) => ({
      activeBizId: null,
      activeBizName: null,
      setActiveBusiness: (bizId, bizName = null) =>
        set({ activeBizId: bizId, activeBizName: bizName }),
      clear: () => set({ activeBizId: null, activeBizName: null }),
    }),
    {
      name: "biz_up_active_business",
      storage: createJSONStorage(() => {
        // SSR 안전 guard — 서버 환경에서는 no-op storage
        if (typeof window === "undefined") {
          return {
            getItem: () => null,
            setItem: () => undefined,
            removeItem: () => undefined,
          };
        }
        return window.localStorage;
      }),
    }
  )
);

/**
 * axios 인터셉터 / 외부 모듈에서 읽기용 — React 외부(비훅) 접근을 위한 헬퍼.
 * React 컴포넌트/훅 안에서는 `useBusinessStore()` 를 직접 사용할 것.
 */
export function getActiveBizIdNonReactive(): string | null {
  return useBusinessStore.getState().activeBizId;
}
