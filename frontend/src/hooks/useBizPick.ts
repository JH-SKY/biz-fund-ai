"use client";

/**
 * 비즈픽 도메인 TanStack Query 훅.
 *
 * - useBizPickList  : 카테고리·정렬 파라미터 기반 목록 쿼리
 * - useBizPickDetail: 상세(모달) 쿼리 — contentId 가 있을 때만 enabled
 * - useLikeBizPick  : like 토글 mutation (Optimistic Update)
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { bizPickService, type BizPickListParams } from "@/lib/services";
import type { BizPickListItem } from "@/types";

export const BIZ_PICK_KEYS = {
  all: ["biz-picks"] as const,
  list: (params: BizPickListParams) =>
    ["biz-picks", "list", params] as const,
  detail: (id: string) => ["biz-picks", "detail", id] as const,
};

/** 카테고리/정렬 목록 */
export function useBizPickList(params: BizPickListParams) {
  return useQuery({
    queryKey: BIZ_PICK_KEYS.list(params),
    queryFn: () => bizPickService.list(params),
    placeholderData: keepPreviousData,
  });
}

/** 상세 (Dialog 열릴 때 트리거) */
export function useBizPickDetail(contentId: string | null) {
  return useQuery({
    queryKey: BIZ_PICK_KEYS.detail(contentId ?? ""),
    queryFn: () => bizPickService.detail(contentId!),
    enabled: !!contentId,
    staleTime: 60_000,
  });
}

/** Like 토글 — Optimistic Update */
export function useLikeBizPick() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (contentId: string) => bizPickService.toggleLike(contentId),

    // Optimistic: 모든 list 캐시에서 해당 아이템의 is_liked / like_count 선행 반전
    onMutate: async (contentId) => {
      await qc.cancelQueries({ queryKey: BIZ_PICK_KEYS.all });

      const snapshots = new Map<readonly unknown[], unknown>();

      qc.getQueriesData<{ items: BizPickListItem[] }>({
        queryKey: BIZ_PICK_KEYS.all,
      }).forEach(([key, data]) => {
        if (!data) return;
        snapshots.set(key, data);
        qc.setQueryData(key, {
          ...data,
          items: data.items.map((item: BizPickListItem) =>
            item.content_id !== contentId
              ? item
              : {
                  ...item,
                  is_liked: !item.is_liked,
                  like_count: item.is_liked
                    ? item.like_count - 1
                    : item.like_count + 1,
                }
          ),
        });
      });
      return { snapshots };
    },

    onError: (_err, _id, ctx) => {
      ctx?.snapshots.forEach((data, key) =>
        qc.setQueryData(key as readonly unknown[], data)
      );
    },

    onSuccess: (res, contentId) => {
      // 서버 응답으로 확정값 보정
      qc.getQueriesData<{ items: BizPickListItem[] }>({
        queryKey: BIZ_PICK_KEYS.all,
      }).forEach(([key, data]) => {
        if (!data) return;
        qc.setQueryData(key, {
          ...data,
          items: data.items.map((item: BizPickListItem) =>
            item.content_id !== contentId
              ? item
              : {
                  ...item,
                  is_liked: res.is_liked,
                  like_count: res.total_likes,
                }
          ),
        });
      });
    },
  });
}
