/**
 * 관리자 전용 Axios 클라이언트.
 *
 * 일반 유저용 api-client.ts 와 완전히 분리된 독립 인스턴스다.
 *  - baseURL: `${NEXT_PUBLIC_API_BASE_URL}` (기본 /api/v1)
 *  - 모든 요청에 `Authorization: Bearer {adminToken}` 자동 첨부
 *  - 응답 envelope `{ status, data, message }` 자동 언래핑
 *  - 401/403 발생 시 admin 세션만 초기화 + /admin/login 리다이렉트
 *    (유저용 refresh-token 로직을 공유하지 않음 — 관리자 세션은 수동 재로그인)
 */

import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

import type { ApiError, ApiResponse } from "@/types";
import {
  clearAdminAuthNonReactive,
  getAdminTokenNonReactive,
} from "@/stores/admin-auth-store";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const DEBUG = process.env.NEXT_PUBLIC_API_DEBUG === "true";

const instance: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
  headers: { "Content-Type": "application/json" },
});

instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAdminTokenNonReactive();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (DEBUG) {
    console.debug(
      `[ADMIN API →] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`,
      config.params ?? "",
      config.data ?? ""
    );
  }
  return config;
});

instance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse<unknown>>) => {
    if (DEBUG) {
      console.debug(
        `[ADMIN API ←] ${response.status} ${response.config.url}`,
        response.data
      );
    }
    const body = response.data;
    if (body && typeof body === "object" && "data" in body) {
      response.data = body.data as never;
    }
    return response;
  },
  async (error: AxiosError<ApiResponse<unknown>>) => {
    // 401/403 → 관리자 세션 강제 만료.
    // 로그인 엔드포인트(/admin/login)는 제외 (잘못된 자격 증명 시 UI에서 에러 표시)
    const url = error.config?.url ?? "";
    if (
      (error.response?.status === 401 || error.response?.status === 403) &&
      !url.includes("/admin/login")
    ) {
      clearAdminAuthNonReactive();
      if (typeof window !== "undefined") {
        const pathname = window.location.pathname;
        if (pathname.startsWith("/admin") && pathname !== "/admin/login") {
          window.location.href = "/admin/login";
        }
      }
    }
    return Promise.reject(normalizeError(error));
  }
);

function normalizeError(error: AxiosError<ApiResponse<unknown>>): ApiError {
  if (error.response) {
    const body = error.response.data;
    const message =
      (body && typeof body === "object" && "message" in body
        ? (body as { message?: string }).message
        : undefined) ?? error.message;
    return {
      status: error.response.status,
      message: message ?? "관리자 요청 처리 중 오류가 발생했습니다.",
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

export const adminApiClient = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    instance.get<unknown, AxiosResponse<T>>(url, config).then((r) => r.data),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    instance
      .post<unknown, AxiosResponse<T>>(url, data, config)
      .then((r) => r.data),
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    instance
      .patch<unknown, AxiosResponse<T>>(url, data, config)
      .then((r) => r.data),
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    instance
      .put<unknown, AxiosResponse<T>>(url, data, config)
      .then((r) => r.data),
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    instance
      .delete<unknown, AxiosResponse<T>>(url, config)
      .then((r) => r.data),
  raw: instance,
};

export default adminApiClient;
