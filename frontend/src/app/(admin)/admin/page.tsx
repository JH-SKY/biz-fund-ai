import { redirect } from "next/navigation";

/**
 * /admin → /admin/dashboard 기본 리다이렉트.
 * 관리자 허브의 진입 경로는 항상 /admin/dashboard 로 통일한다.
 */
export default function AdminRootPage() {
  redirect("/admin/dashboard");
}
