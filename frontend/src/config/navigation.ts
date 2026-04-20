/**
 * 앱 전역 내비게이션 정의 — 한 곳에서 관리하여 Sidebar / BottomTab / Breadcrumb 이
 * 동일한 메뉴 구조를 공유한다.
 */

import {
  LayoutDashboard,
  Target,
  MessageSquareHeart,
  Newspaper,
  User,
  FolderOpen,
  Bell,
  History,
  type LucideIcon,
} from "lucide-react";
import type { Route } from "next";

export interface NavItem {
  key: string;
  label: string;
  href: Route;
  icon: LucideIcon;
  /** 모바일 하단 탭바에도 노출할지 */
  showInBottomTab?: boolean;
  /** 활성 상태 매칭용 prefix (예: /chat/123 도 /chat 으로 매칭) */
  matchPrefix?: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    key: "dashboard",
    label: "대시보드",
    href: "/dashboard",
    icon: LayoutDashboard,
    showInBottomTab: true,
    matchPrefix: "/dashboard",
  },
  {
    key: "policies",
    label: "맞춤 정책",
    // 사이드바/탭바 클릭 시 기본적으로 '맞춤'(P06)으로 진입 — '/policies' 는 전체 탐색(P05).
    href: "/policies/matching",
    icon: Target,
    showInBottomTab: true,
    matchPrefix: "/policies",
  },
  {
    key: "chat",
    label: "AI 상담",
    href: "/chat",
    icon: MessageSquareHeart,
    showInBottomTab: true,
    matchPrefix: "/chat",
  },
  {
    key: "picks",
    label: "비즈픽",
    href: "/picks",
    icon: Newspaper,
    showInBottomTab: true,
    matchPrefix: "/picks",
  },
  {
    key: "profile",
    label: "마이페이지",
    href: "/profile",
    icon: User,
    showInBottomTab: true,
    matchPrefix: "/profile",
  },
  {
    key: "documents",
    label: "서류 보관함",
    href: "/documents",
    icon: FolderOpen,
    showInBottomTab: false,
    matchPrefix: "/documents",
  },
  {
    key: "notifications",
    label: "알림",
    href: "/notifications",
    icon: Bell,
    showInBottomTab: false,
    matchPrefix: "/notifications",
  },
  {
    key: "history",
    label: "히스토리",
    href: "/history",
    icon: History,
    showInBottomTab: false,
    matchPrefix: "/history",
  },
];

export function isActivePath(pathname: string, item: NavItem): boolean {
  const target = item.matchPrefix ?? item.href;
  return pathname === target || pathname.startsWith(target + "/");
}
