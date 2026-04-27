"use client";

/**
 * [P06] /policies/matching — 내 맞춤 정책 (Personalized Matching).
 *
 * 데이터 소스: GET /policies/recommend (PolicyRecommendItem[])
 *  - 신호등(match_level), 적합도(match_score), 매칭 근거(reason) 제공.
 *  - completeness_tier: L1(기본 프로필) / L2(재무 포함) 로 단계 구분.
 *    L1: 전체 목록 노출 + 재무 입력 유도 CTA 배너
 *    L2: estimated_probability 노출 활성
 *
 * UI 구성
 *  1. 상단 탭(맞춤/전체) — 전체 리스트와의 이동
 *  2. 상태 탭(전체/신규/마감임박/인기) — 현재 백엔드 필드 부족으로 클라이언트 필터
 *     · 신규/마감임박/인기는 향후 API 확장 전까지는 match_score 기반 heuristic 으로 분류
 *  3. MatchingPolicyCard 리스트 (AI 요약 배지, 매칭 근거 문구)
 */

import { useMemo, useState } from "react";
import Link from "next/link";

import { Tabs } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { MatchingPolicyCard } from "@/features/policies/MatchingPolicyCard";
import { PolicyEmptyState } from "@/features/policies/PolicyEmptyState";
import { PolicyListSkeleton } from "@/features/policies/PolicyListSkeleton";
import { PolicyPageTabs } from "@/features/policies/PolicyPageTabs";
import { useBookmarkToggle, useRecommendedPolicies } from "@/hooks/usePolicies";
import type { PolicyRecommendItem } from "@/types";

type StatusTab = "all" | "new" | "urgent" | "hot";

interface DecoratedItem extends PolicyRecommendItem {
  statusTag: "new" | "urgent" | "hot" | null;
  dday: string | null;
}

/**
 * 백엔드 PolicyRecommendItem 에 closed_at/created_at 필드가 없어
 * 현재는 match_score 를 기준으로 신규/마감임박/인기 태그를 휴리스틱 지정.
 * (실 서비스 연동 시 closed_at 등 원본 필드 추가 필요)
 */
function decorate(item: PolicyRecommendItem, idx: number): DecoratedItem {
  let statusTag: DecoratedItem["statusTag"] = null;
  if (idx < 2) statusTag = "hot";
  else if (idx < 4) statusTag = "new";
  else if (item.match_score >= 80) statusTag = "urgent";

  return { ...item, statusTag, dday: null };
}

export default function MatchingPoliciesPage() {
  const [tab, setTab] = useState<StatusTab>("all");
  const { data, isLoading, isError, refetch } = useRecommendedPolicies();
  const bookmarkMutation = useBookmarkToggle();

  const unverifiedNotice = data?.unverified_notice ?? null;
  const tier = data?.completeness_tier ?? "L1";
  const upgradeHint = data?.upgrade_hint ?? null;

  const decorated: DecoratedItem[] = useMemo(
    () => (data?.items ?? []).map((i, idx) => decorate(i, idx)),
    [data?.items]
  );

  const filtered = useMemo(() => {
    if (tab === "all") return decorated;
    return decorated.filter((d) => {
      if (tab === "new") return d.statusTag === "new";
      if (tab === "urgent") return d.statusTag === "urgent";
      if (tab === "hot") return d.statusTag === "hot";
      return true;
    });
  }, [decorated, tab]);

  const counts = useMemo(
    () => ({
      all: decorated.length,
      new: decorated.filter((d) => d.statusTag === "new").length,
      urgent: decorated.filter((d) => d.statusTag === "urgent").length,
      hot: decorated.filter((d) => d.statusTag === "hot").length,
    }),
    [decorated]
  );

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1>맞춤 정책</h1>
        <p className="text-sm text-ink-secondary">
          사장님의 프로필 데이터를 기반으로 AI 가 추천한 정책만 보여드립니다.
        </p>
      </header>

      <PolicyPageTabs active="matching" />

      {/* L1 단계 유도 배너 */}
      {tier === "L1" && upgradeHint ? (
        <div
          role="status"
          className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="text-sm font-medium text-blue-900">
                🔍 지금은 1차 맞춤 추천입니다
              </p>
              <p className="text-xs text-blue-700">{upgradeHint}</p>
            </div>
            <Link href="/profile">
              <Button size="sm" variant="outline" className="shrink-0 border-blue-300 text-blue-700 hover:bg-blue-100">
                재무 입력 →
              </Button>
            </Link>
          </div>
        </div>
      ) : tier === "L2" ? (
        <div
          role="status"
          className="rounded-xl border border-green-200 bg-green-50 px-4 py-2 text-xs text-green-800"
        >
          ✅ 재무정보 반영 완전 맞춤 — 추정 확률이 카드에 표시됩니다
        </div>
      ) : null}

      {unverifiedNotice ? (
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          {unverifiedNotice}
        </div>
      ) : null}

      <Tabs
        variant="pill"
        value={tab}
        onValueChange={(v) => setTab(v as StatusTab)}
        items={[
          { value: "all", label: "전체", count: counts.all },
          { value: "new", label: "신규", count: counts.new },
          { value: "urgent", label: "마감임박", count: counts.urgent },
          { value: "hot", label: "인기", count: counts.hot },
        ]}
      />

      {isLoading ? (
        <PolicyListSkeleton count={5} />
      ) : isError ? (
        <div className="rounded-xl border border-danger-200 bg-danger-50 p-6 text-sm text-danger-800">
          맞춤 정책을 불러오지 못했습니다.
          <Button variant="link" size="sm" onClick={() => refetch()}>
            다시 시도
          </Button>
        </div>
      ) : filtered.length === 0 ? (
        <PolicyEmptyState
          title="해당 조건의 맞춤 정책이 없습니다."
          description="다른 탭을 확인하거나, 프로필 정보를 최신으로 유지해보세요."
          onReset={() => setTab("all")}
        />
      ) : (
        <ul className="space-y-3">
          {filtered.map((item) => (
            <li key={item.policy_id}>
              <MatchingPolicyCard
                policyId={item.policy_id}
                title={item.title}
                matchLevel={item.match_level}
                matchScore={item.match_score}
                reason={item.reason}
                estimatedProbability={item.estimated_probability}
                isBookmarked={item.is_bookmarked}
                statusTag={item.statusTag}
                dday={item.dday}
                tier={tier}
                onBookmarkToggle={(id) => bookmarkMutation.mutate(id)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
