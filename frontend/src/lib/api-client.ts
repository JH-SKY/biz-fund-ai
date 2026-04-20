/**
 * Axios 기반 API 클라이언트.
 *
 * 설계 원칙 (.cursorrules §5 권장 기술 스택 준수)
 *  1) 백엔드 공통 응답 envelope `{ status, data, message }` 를 인터셉터에서 자동 언래핑
 *     → 호출부에서는 `apiClient.get<T>(...)` 결과가 곧바로 `T` 가 되도록 한다.
 *  2) Access Token 자동 첨부 + 401 시 Refresh Token 로테이션 → 재시도.
 *  3) 네트워크/서버 오류를 ApiError 로 정규화하여 호출부 `try/catch` 통일.
 *  4) 개발 모드(NEXT_PUBLIC_API_DEBUG=true)에서는 요청/응답 로그를 콘솔에 출력.
 */

import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

import type { ApiError, ApiResponse } from "@/types";
import { getActiveBizIdNonReactive } from "@/stores/business-store";
import {
  getAccessTokenNonReactive,
  getRefreshTokenNonReactive,
} from "@/stores/auth-store";

// ── 환경 변수 ──────────────────────────────────────────────────────
const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const DEBUG = process.env.NEXT_PUBLIC_API_DEBUG === "true";

// ── 토큰 저장소 (auth-store 위임) ────────────────────────────────────
// auth-store 가 Zustand persist 로 localStorage 에 이미 저장하므로
// 여기서는 스토어를 통해 읽기/쓰기만 수행한다.
export const tokenStorage = {
  getAccess(): string | null {
    return getAccessTokenNonReactive();
  },
  getRefresh(): string | null {
    return getRefreshTokenNonReactive();
  },
  set(access: string, refresh?: string) {
    // auth-store 에 위임 (dynamic import 로 순환 의존 방지)
    import("@/stores/auth-store").then(({ useAuthStore }) => {
      useAuthStore.getState().setTokens(access, refresh);
    });
  },
  clear() {
    import("@/stores/auth-store").then(({ useAuthStore }) => {
      useAuthStore.getState().logout();
    });
  },
};

// ── Axios 인스턴스 ─────────────────────────────────────────────────
const axiosInstance: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── 요청 인터셉터: Access Token + X-Business-Id 자동 첨부 ────────
axiosInstance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccess();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // X-Business-Id — 스토어에 활성 사업장이 있으면 자동 첨부.
  // 호출부에서 명시적으로 null/빈 문자열을 세팅한 경우엔 건너뛰어 오버라이드 허용.
  if (config.headers && !("X-Business-Id" in config.headers)) {
    const bizId = getActiveBizIdNonReactive();
    if (bizId) {
      config.headers["X-Business-Id"] = bizId;
    }
  }

  if (DEBUG) {
    console.debug(
      `[API →] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`,
      config.params ?? "",
      config.data ?? ""
    );
  }
  return config;
});

// ── 토큰 재발급 (401 핸들링) ──────────────────────────────────────
let isRefreshing = false;
let refreshQueue: Array<(token: string | null) => void> = [];

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshTokenNonReactive();
  if (!refresh) return null;

  try {
    const resp = await axios.post<ApiResponse<{ access_token: string }>>(
      `${BASE_URL}/auth/refresh`,
      { refresh_token: refresh },
      { headers: { "Content-Type": "application/json" } }
    );
    const newAccess = resp.data?.data?.access_token;
    if (newAccess) {
      tokenStorage.set(newAccess, refresh);
      return newAccess;
    }
    return null;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

// ── 응답 인터셉터: envelope 언래핑 + 에러 정규화 ─────────────────
axiosInstance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse<unknown>>) => {
    if (DEBUG) {
      console.debug(
        `[API ←] ${response.status} ${response.config.url}`,
        response.data
      );
    }
    // 백엔드 envelope: { status, data, message } → data 만 반환
    const body = response.data;
    if (body && typeof body === "object" && "data" in body) {
      // AxiosResponse 객체 전체를 반환해야 하므로 data 필드를 교체
      response.data = body.data as never;
    }
    return response;
  },
  async (error: AxiosError<ApiResponse<unknown>>) => {
    const originalRequest = error.config as
      | (AxiosRequestConfig & { _retry?: boolean })
      | undefined;

    // 401 → 토큰 재발급 후 재시도
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/")
    ) {
      originalRequest._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push((token) => {
            if (!token) {
              reject(normalizeError(error));
              return;
            }
            originalRequest.headers = {
              ...originalRequest.headers,
              Authorization: `Bearer ${token}`,
            };
            resolve(axiosInstance(originalRequest));
          });
        });
      }

      isRefreshing = true;
      const newToken = await refreshAccessToken();
      isRefreshing = false;
      refreshQueue.forEach((cb) => cb(newToken));
      refreshQueue = [];

      if (newToken) {
        originalRequest.headers = {
          ...originalRequest.headers,
          Authorization: `Bearer ${newToken}`,
        };
        return axiosInstance(originalRequest);
      }

      // 재발급 실패 → 스토어 초기화 (AppGuard 가 /login 리다이렉트를 담당)
      tokenStorage.clear();
    }

    return Promise.reject(normalizeError(error));
  }
);

/** AxiosError → ApiError 정규화 */
function normalizeError(error: AxiosError<ApiResponse<unknown>>): ApiError {
  if (error.response) {
    const body = error.response.data;
    const message =
      (body && typeof body === "object" && "message" in body
        ? (body as { message?: string }).message
        : undefined) ?? error.message;
    return {
      status: error.response.status,
      message: message ?? "요청 처리 중 오류가 발생했습니다.",
      code: error.code,
      detail: body,
    };
  }
  if (error.request) {
    return {
      status: 0,
      message: "서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.",
      code: error.code,
    };
  }
  return { status: -1, message: error.message, code: error.code };
}

// ── 제네릭 Wrapper ─────────────────────────────────────────────────
// 응답 인터셉터에서 envelope.data 를 response.data 로 치환했으므로
// 호출부는 T 만 받아 사용하면 된다.
export const apiClient = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    axiosInstance.get<unknown, AxiosResponse<T>>(url, config).then((r) => r.data),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance
      .post<unknown, AxiosResponse<T>>(url, data, config)
      .then((r) => r.data),
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance
      .patch<unknown, AxiosResponse<T>>(url, data, config)
      .then((r) => r.data),
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance
      .put<unknown, AxiosResponse<T>>(url, data, config)
      .then((r) => r.data),
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    axiosInstance
      .delete<unknown, AxiosResponse<T>>(url, config)
      .then((r) => r.data),
  raw: axiosInstance,
};

export default apiClient;
