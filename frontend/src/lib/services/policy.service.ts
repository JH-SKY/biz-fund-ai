/**
 * 정책(policy) 도메인 API 서비스.
 *
 * 백엔드 매핑 (backend/src/app/api/v1/policy_router.py)
 *  - GET  /policies                   → fetchAllPolicies
 *  - GET  /policies/recommend         → fetchRecommendedPolicies  ← [대시보드 '원픽']
 *  - GET  /policies/bookmarks         → fetchBookmarkedPolicies
 *  - GET  /policies/search            → searchPolicies
 *  - GET  /policies/{id}              → fetchPolicyDetail
 *  - POST /policies/{id}/bookmark     → toggleBookmark
 *
 * ※ X-Business-Id 헤더는 api-client 인터셉터에서 자동 첨부된다.
 */

import apiClient from "@/lib/api-client";
import type {
  BookmarkToggleResponse,
  PolicyDetail,
  PolicyListItem,
  PolicyRecommendItem,
  PolicySearchParams,
} from "@/types";

interface ListResponse {
  items: PolicyListItem[];
  total_count: number;
  total_pages: number;
}

interface RecommendResponse {
  items: PolicyRecommendItem[];
}

export const policyService = {
  fetchAllPolicies: (page = 1, size = 10) =>
    apiClient.get<ListResponse>("/policies", { params: { page, size } }),

  fetchRecommendedPolicies: (page = 1, size = 10) =>
    apiClient.get<RecommendResponse>("/policies/recommend", {
      params: { page, size },
    }),

  fetchBookmarkedPolicies: (page = 1, size = 10) =>
    apiClient.get<ListResponse>("/policies/bookmarks", {
      params: { page, size },
    }),

  searchPolicies: (params: PolicySearchParams) =>
    apiClient.get<ListResponse>("/policies/search", { params }),

  fetchPolicyDetail: (policyId: string) =>
    apiClient.get<PolicyDetail>(`/policies/${policyId}`),

  toggleBookmark: (policyId: string) =>
    apiClient.post<BookmarkToggleResponse>(`/policies/${policyId}/bookmark`),
};
