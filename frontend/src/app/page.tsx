"use client";

/**
 * [P01] 랜딩 페이지 (`/`) — 비로그인 전용.
 *
 * 섹션
 *  1) 미니 헤더(로고 + 로그인 CTA)
 *  2) Hero: 카운트업 예산 전광판
 *  3) Quick Match: 지역·업종 → 결과 Modal
 *  4) Service Preview: 비즈픽·비즈핑·비즈몽 블러 미리보기
 *  5) 푸터
 *
 * TODO(인증 연동 후)
 *  - 로그인 세션 확인 시 router.replace("/dashboard")
 *  - 현재는 미구현이므로 주석으로 위치만 표시
 */

import Link from "next/link";
import { useState } from "react";
import { Rocket } from "lucide-react";

import { Button } from "@/components/ui/button";
import { HeroCounter } from "@/features/landing/HeroCounter";
import {
  QuickMatchWidget,
  type LandingFilter,
} from "@/features/landing/QuickMatchWidget";
import { QuickMatchModal } from "@/features/landing/QuickMatchModal";
import { ServicePreview } from "@/features/landing/ServicePreview";

// 2026년 정책자금 총액(원) — 기획서 §2-① 예시 수치
const POLICY_BUDGET_TOTAL = 26_450_000_000_000;

export default function LandingPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [filter, setFilter] = useState<LandingFilter>({
    region: "",
    industry: "",
  });

  // TODO: 로그인 세션 검증 후 /dashboard 리다이렉트
  // useEffect(() => { if (isAuthenticated) router.replace("/dashboard"); }, []);

  const handleQuickSubmit = (f: LandingFilter) => {
    setFilter(f);
    setModalOpen(true);
  };

  return (
    <main className="min-h-dvh bg-gradient-to-b from-primary-50 via-surface to-surface">
      {/* ── 1) 미니 헤더 ─────────────────────────────────────── */}
      <nav className="sticky top-0 z-20 bg-surface/80 backdrop-blur border-b border-surface-border/60">
        <div className="mx-auto flex h-header max-w-[var(--content-max)] items-center justify-between px-4 sm:px-6">
          <Link
            href="/"
            className="flex items-center gap-2"
            aria-label="Biz-Up 홈"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600 text-white">
              <Rocket className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold">Biz-Up</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                로그인
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="primary" size="sm">
                무료로 시작하기
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ── 2) Hero ──────────────────────────────────────────── */}
      <section className="mx-auto max-w-[var(--content-max)] px-4 pt-12 pb-10 sm:px-6 sm:pt-20 sm:pb-14">
        <HeroCounter target={POLICY_BUDGET_TOTAL} />
      </section>

      {/* ── 3) Quick Match ───────────────────────────────────── */}
      <section
        aria-label="퀵 매칭"
        className="mx-auto flex max-w-[var(--content-max)] flex-col items-center px-4 pb-16 sm:px-6 sm:pb-24"
      >
        <QuickMatchWidget onSubmit={handleQuickSubmit} />
      </section>

      {/* ── 4) Service Preview ──────────────────────────────── */}
      <section className="bg-surface-muted py-16 sm:py-20">
        <div className="mx-auto max-w-[var(--content-max)] px-4 sm:px-6">
          <ServicePreview />
        </div>
      </section>

      {/* ── 5) 푸터 ──────────────────────────────────────────── */}
      <footer className="border-t border-surface-border bg-surface py-8">
        <div className="mx-auto flex max-w-[var(--content-max)] flex-col items-center justify-between gap-2 px-4 text-xs text-ink-tertiary sm:flex-row sm:px-6">
          <div>© {new Date().getFullYear()} Biz-Up. 사장님을 위한 AI 정책자금 비서.</div>
          <div className="flex items-center gap-4">
            <a href="#" className="hover:text-ink-secondary">
              이용약관
            </a>
            <a href="#" className="hover:text-ink-secondary">
              개인정보처리방침
            </a>
            <a href="#" className="hover:text-ink-secondary">
              고객센터
            </a>
          </div>
        </div>
      </footer>

      {/* Modal */}
      <QuickMatchModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        region={filter.region}
        industry={filter.industry}
      />
    </main>
  );
}
