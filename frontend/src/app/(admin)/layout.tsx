"use client";

/**
 * (admin) route group — 관리자 센터 전용 레이아웃.
 *
 * 일반 (app) / (auth) 와 완전히 독립된 라우트 그룹.
 * 각 하위 페이지가 자체 가드를 선언한다:
 *  - /admin/login: AdminPublicGuard (이미 로그인된 관리자 차단)
 *  - /admin/*    : AdminGuard (비로그인 차단)
 *
 * 여기서 AdminShell 을 공통 적용하지 않는 이유는 로그인 페이지가
 * 사이드바 없는 풀스크린 디자인을 사용하기 때문.
 */

import type { ReactNode } from "react";

export default function AdminRouteGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <>{children}</>;
}
