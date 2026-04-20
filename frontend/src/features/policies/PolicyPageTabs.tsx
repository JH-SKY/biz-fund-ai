"use client";

/**
 * 정책 상위 네비게이션: 맞춤(P06) ↔ 전체(P05) 토글.
 * 두 페이지에 공통 배치하여 탐색 맥락을 이어준다.
 */

import { useRouter } from "next/navigation";
import { Tabs } from "@/components/ui/tabs";

type PolicyTab = "matching" | "all";

interface Props {
  active: PolicyTab;
}

export function PolicyPageTabs({ active }: Props) {
  const router = useRouter();
  return (
    <Tabs
      variant="underline"
      value={active}
      onValueChange={(v) =>
        router.push(v === "matching" ? "/policies/matching" : "/policies")
      }
      items={[
        { value: "matching", label: "맞춤 정책" },
        { value: "all", label: "전체 정책" },
      ]}
    />
  );
}
