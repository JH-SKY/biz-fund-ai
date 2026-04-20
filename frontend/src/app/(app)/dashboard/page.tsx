"use client";

/**
 * [PAGE 04] 메인 대시보드 (/dashboard)
 *
 * 구성 (.cursorrules P04 스펙 + PAGE 04 상세 기획안)
 *
 *  ┌────────────────────── 환영 섹션 ──────────────────────┐
 *  │ 안녕하세요, OOO 사장님 👋                              │
 *  └───────────────────────────────────────────────────────┘
 *  ┌─ 좌측 (맞춤 브리핑/통계) ─┬─ 우측 (정밀 진단/트래커) ─┐
 *  │  ① 맞춤 정책 건수 + 비즈몽│  ① 원픽 카드              │
 *  │  ② 혜택 수준 인포그래픽   │  ② 사업장 신호등 위젯      │
 *  │  ③ 오늘의 꿀팁/비즈-픽    │  ③ 상태 트래커            │
 *  │                          │  ④ 등록 서류 현황          │
 *  └──────────────────────────┴───────────────────────────┘
 *
 * 데이터 동기화 전략
 *  - `useMyBusiness()`         → 사업장 정보 (없으면 온보딩 유도)
 *  - `useRecommendedPolicies`  → 원픽 + 맞춤 건수 + 혜택 비교
 *  - `useDiagnosisHistory`     → 신호등 정밀 진단 점수
 *  - `useMyDocuments`          → 등록 서류 현황 + 신호등 보정
 *
 * 인증 게이트
 *  - 로그인 + 온보딩이 모두 완료돼야 본 화면 정상 노출.
 *  - 현 단계(Phase 1)에서는 /onboarding 으로 강제 리다이렉트 대신
 *    상단 배너를 띄워 라우팅 책임을 라우트 가드 도입 시점까지 유예한다.
 */

import { useEffect, useMemo } from "react";

import {
  ApplicationStatusTracker,
  BenefitLevelCard,
  DocumentsWidget,
  InsightTipCard,
  MatchSummaryCard,
  OnePickSection,
  TrafficLightWidget,
  WelcomeHeader,
} from "@/components/dashboard";
import {
  useDiagnosisHistory,
  useMyBusiness,
  useMyDocuments,
  useRecommendedPolicies,
  useToggleBookmark,
} from "@/hooks/useDashboard";
import { useBusinessStore } from "@/stores/business-store";

export default function DashboardPage() {
  const setActiveBusiness = useBusinessStore((s) => s.setActiveBusiness);
  const activeBizId = useBusinessStore((s) => s.activeBizId);

  const bizQ = useMyBusiness();
  const recQ = useRecommendedPolicies({ size: 10 });
  const diagQ = useDiagnosisHistory();
  const docsQ = useMyDocuments();
  const bookmarkMut = useToggleBookmark();

  // 사업장 조회 성공 → 스토어에 자동 반영 (이후 API 는 X-Business-Id 헤더 자동 첨부)
  useEffect(() => {
    if (bizQ.data?.biz_id && bizQ.data.biz_id !== activeBizId) {
      setActiveBusiness(bizQ.data.biz_id, bizQ.data.biz_name);
    }
  }, [bizQ.data, activeBizId, setActiveBusiness]);

  // 집계 지표 계산
  const matchedCount = recQ.data?.items?.length ?? null;
  const myAvgScore = useMemo(() => {
    const items = recQ.data?.items;
    if (!items?.length) return null;
    const sum = items.reduce((acc, it) => acc + (it.match_score ?? 0), 0);
    return sum / items.length;
  }, [recQ.data]);

  const latestDiagnosisScore =
    diagQ.data && diagQ.data.length > 0 ? diagQ.data[0].score : null;

  // 온보딩 미완료 판정: 404 → 사업장 없음
  const isOnboarded = Boolean(bizQ.data?.biz_id);

  return (
    <div className="space-y-6 pb-8">
      <WelcomeHeader
        business={bizQ.data}
        isLoading={bizQ.isLoading}
        isOnboarded={isOnboarded}
      />

      {/* 2-컬럼 레이아웃: Desktop 에서만 분할, 모바일은 1-컬럼 */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* ── 좌측: 맞춤 브리핑 & 통계 ───────────────────── */}
        <section className="space-y-4 lg:col-span-7">
          <MatchSummaryCard
            matchedCount={matchedCount}
            isLoading={recQ.isLoading}
          />
          <BenefitLevelCard myAvgScore={myAvgScore} />
          <InsightTipCard />
        </section>

        {/* ── 우측: 정밀 진단 & 트래커 ───────────────────── */}
        <aside className="space-y-4 lg:col-span-5">
          <OnePickSection
            items={recQ.data?.items}
            isLoading={recQ.isLoading}
            onBookmarkToggle={(id) => bookmarkMut.mutate(id)}
          />
          <TrafficLightWidget
            business={bizQ.data}
            latestDiagnosisScore={latestDiagnosisScore}
            documents={docsQ.data}
            isLoading={bizQ.isLoading}
          />
          <ApplicationStatusTracker latestApplication={null} />
          <DocumentsWidget documents={docsQ.data} isLoading={docsQ.isLoading} />
        </aside>
      </div>
    </div>
  );
}
