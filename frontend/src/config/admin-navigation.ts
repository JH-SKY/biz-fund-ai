/**
 * 관리자 센터 내비게이션.
 *
 * PAGE 12 기획안의 4개 섹션 + 기존 운영 도구를 통합하여 11개 메뉴로 구성.
 *  ① 로직 디버깅 / 피드백 센터
 *  ② 시스템 건강 / 비용
 *  ③ 비즈픽 콘텐츠
 *  ④ 비즈니스 인사이트
 *  + 유저 / 채팅 / 감사 / 배치 / 정책 (운영)
 */

import {
  LayoutDashboard,
  MessageCircleWarning,
  Activity,
  Users,
  MessageSquareText,
  ScrollText,
  Cpu,
  Layers,
  Newspaper,
  TrendingUp,
} from "lucide-react";
import type { Route } from "next";

import type { NavItem } from "./navigation";

export interface AdminNavSection {
  section: string;
  items: Array<NavItem & { href: Route }>;
}

export const ADMIN_NAV_SECTIONS: AdminNavSection[] = [
  {
    section: "개요",
    items: [
      {
        key: "admin-dashboard",
        label: "대시보드",
        href: "/admin/dashboard",
        icon: LayoutDashboard,
        matchPrefix: "/admin/dashboard",
      },
    ],
  },
  {
    section: "AI 품질 관리",
    items: [
      {
        key: "admin-feedback",
        label: "피드백 · 오답 정정",
        href: "/admin/feedback",
        icon: MessageCircleWarning,
        matchPrefix: "/admin/feedback",
      },
      {
        key: "admin-monitoring",
        label: "시스템 건강 · 비용",
        href: "/admin/monitoring",
        icon: Activity,
        matchPrefix: "/admin/monitoring",
      },
    ],
  },
  {
    section: "운영",
    items: [
      {
        key: "admin-users",
        label: "유저 관리",
        href: "/admin/users",
        icon: Users,
        matchPrefix: "/admin/users",
      },
      {
        key: "admin-chat-logs",
        label: "채팅 모니터링",
        href: "/admin/chat-logs",
        icon: MessageSquareText,
        matchPrefix: "/admin/chat-logs",
      },
      {
        key: "admin-audit",
        label: "감사 로그",
        href: "/admin/audit-logs",
        icon: ScrollText,
        matchPrefix: "/admin/audit-logs",
      },
      {
        key: "admin-batch",
        label: "정책 수집 현황",
        href: "/admin/batch",
        icon: Cpu,
        matchPrefix: "/admin/batch",
      },
    ],
  },
  {
    section: "콘텐츠 & 정책",
    items: [
      {
        key: "admin-policies",
        label: "정책 관리",
        href: "/admin/policies",
        icon: Layers,
        matchPrefix: "/admin/policies",
      },
      {
        key: "admin-contents",
        label: "비즈픽 콘텐츠",
        href: "/admin/contents",
        icon: Newspaper,
        matchPrefix: "/admin/contents",
      },
    ],
  },
  {
    section: "비즈니스 전략",
    items: [
      {
        key: "admin-insights",
        label: "미충족 수요 · 전환",
        href: "/admin/insights",
        icon: TrendingUp,
        matchPrefix: "/admin/insights",
      },
    ],
  },
];

/** 단일 배열이 필요한 경우 평탄화 헬퍼 */
export const ADMIN_NAV_ITEMS: NavItem[] = ADMIN_NAV_SECTIONS.flatMap(
  (s) => s.items
);

export function isActiveAdminPath(pathname: string, item: NavItem): boolean {
  const target = item.matchPrefix ?? item.href;
  return pathname === target || pathname.startsWith(target + "/");
}
