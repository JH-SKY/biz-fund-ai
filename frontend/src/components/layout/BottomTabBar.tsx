"use client";

/**
 * 모바일 하단 탭바 (<lg 에서만 노출).
 * iOS 홈바 영역을 피하기 위해 safe-pb(env(safe-area-inset-bottom)) 적용.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { NAV_ITEMS, isActivePath } from "@/config/navigation";

export function BottomTabBar() {
  const pathname = usePathname();
  const tabs = NAV_ITEMS.filter((item) => item.showInBottomTab);

  return (
    <nav
      aria-label="하단 메뉴"
      className={cn(
        "lg:hidden fixed inset-x-0 bottom-0 z-30",
        "bg-surface/95 backdrop-blur border-t border-surface-border",
        "safe-pb"
      )}
    >
      <ul className="flex h-bottom-tab items-stretch">
        {tabs.map((item) => {
          const active = isActivePath(pathname, item);
          const Icon = item.icon;
          return (
            <li key={item.key} className="flex-1">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-full flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors",
                  active
                    ? "text-primary-600"
                    : "text-ink-tertiary hover:text-ink-secondary"
                )}
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
