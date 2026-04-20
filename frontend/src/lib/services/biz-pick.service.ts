/**
 * 비즈픽 (biz_pick) 도메인 API 서비스.
 *
 * 백엔드 매핑
 *  - GET  /biz-picks               → list (category·sort 필터)
 *  - GET  /biz-picks/{id}          → detail (body_html, related_policies, tags)
 *  - POST /biz-picks/{id}/like     → like 토글 → BizPickLikeResponse
 *
 * ※ X-Business-Id 헤더는 api-client 인터셉터에서 자동 첨부된다.
 *    비로그인 사용자에게도 목록은 공개되나, like 는 인증 필요.
 */

import apiClient from "@/lib/api-client";
import type { BizPickDetail, BizPickLikeResponse, BizPickListItem, Paginated } from "@/types";

export interface BizPickListParams {
  category?: string;
  sort?: "latest" | "popular";
  page?: number;
  size?: number;
}

export const bizPickService = {
  list(params: BizPickListParams = {}) {
    return apiClient.get<Paginated<BizPickListItem>>("/biz-picks", { params });
  },

  detail(contentId: string) {
    return apiClient.get<BizPickDetail>(`/biz-picks/${contentId}`);
  },

  toggleLike(contentId: string) {
    return apiClient.post<BizPickLikeResponse>(`/biz-picks/${contentId}/like`);
  },
};
