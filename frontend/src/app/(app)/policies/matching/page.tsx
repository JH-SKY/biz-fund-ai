"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { MatchingPolicyCard } from "@/features/policies/MatchingPolicyCard";
import { PolicyEmptyState } from "@/features/policies/PolicyEmptyState";
import { PolicyListSkeleton } from "@/features/policies/PolicyListSkeleton";
import { PolicyPageTabs } from "@/features/policies/PolicyPageTabs";
import { useBookmarkToggle, useRecommendedPolicies } from "@/hooks/usePolicies";

export default function MatchingPoliciesPage() {
  const { data, isLoading, isError, refetch } = useRecommendedPolicies();
  const bookmarkMutation = useBookmarkToggle();

  const tier = data?.completeness_tier ?? "L1";
  const upgradeHint = data?.upgrade_hint ?? null;
  const unverifiedNotice = data?.unverified_notice ?? null;
  const items = data?.items ?? [];

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1>맞춤 정책</h1>
        <p className="text-sm text-ink-secondary">
          사업 정보와 재무 정보를 기준으로 실제 조건에 맞는 정책만 먼저 추려서 보여줍니다.
        </p>
      </header>

      <PolicyPageTabs active="matching" />

      {tier === "L1" ? (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="text-sm font-medium text-blue-900">
                지금은 1차 정보 기준 후보 정책만 조심스럽게 보여주고 있어요.
              </p>
              <p className="text-xs text-blue-700">
                {upgradeHint ?? "재무 정보를 입력하면 실제 자격 조건까지 반영한 정밀 추천으로 바뀝니다."}
              </p>
            </div>
            <Link href={"/diagnosis" as never}>
              <Button
                size="sm"
                variant="outline"
                className="shrink-0 border-blue-300 text-blue-700 hover:bg-blue-100"
              >
                정밀진단 받고 정확하게 추천받기
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3">
          <p className="text-sm font-medium text-green-900">
            정밀진단을 반영한 맞춤 정책 추천 결과입니다.
          </p>
          <p className="mt-0.5 text-xs text-green-700">
            정책 조건과 재무 조건을 함께 반영해 우선순위를 다시 계산했습니다.
          </p>
        </div>
      )}

      {unverifiedNotice ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {unverifiedNotice}
        </div>
      ) : null}

      {isLoading ? (
        <PolicyListSkeleton count={5} />
      ) : isError ? (
        <div className="rounded-xl border border-danger-200 bg-danger-50 p-6 text-sm text-danger-800">
          맞춤 정책을 불러오지 못했습니다.
          <Button variant="link" size="sm" onClick={() => refetch()}>
            다시 시도
          </Button>
        </div>
      ) : items.length === 0 ? (
        <PolicyEmptyState
          title="현재 입력 정보 기준으로 바로 추천할 정책이 없습니다."
          description="사업 정보나 재무 정보를 조금 더 보완하면 후보군이 다시 넓어질 수 있습니다."
          onReset={() => refetch()}
        />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.policy_id}>
              <MatchingPolicyCard
                policyId={item.policy_id}
                title={item.title}
                matchLevel={item.match_level}
                matchScore={item.match_score}
                reason={item.reason}
                estimatedProbability={item.estimated_probability}
                isBookmarked={item.is_bookmarked}
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
