import {
  Bell,
  History,
  LayoutDashboard,
  MessageSquareHeart,
  Newspaper,
  Target,
  User,
  type LucideIcon,
} from "lucide-react";
import type { Route } from "next";

export interface NavItem {
  key: string;
  label: string;
  href: Route;
  icon: LucideIcon;
  showInBottomTab?: boolean;
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
    label: "BizPick",
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
