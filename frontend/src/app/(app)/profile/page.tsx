"use client";

import * as React from "react";
import { Tabs } from "@/components/ui/tabs";
import { BusinessInfoTab } from "@/features/profile/BusinessInfoTab";
import { FinancialTab } from "@/features/profile/FinancialTab";
import { AccountSettingsTab } from "@/features/profile/AccountSettingsTab";

const TABS = [
  { value: "business", label: "사업장 정보" },
  { value: "financial", label: "재무 현황" },
  { value: "account", label: "계정 설정" },
];

export default function ProfilePage() {
  const [tab, setTab] = React.useState("business");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">마이페이지</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          사업장 정보·재무 현황·계정 설정을 관리합니다.
        </p>
      </div>

      <Tabs
        value={tab}
        onValueChange={setTab}
        items={TABS}
        variant="underline"
      />

      <div>
        {tab === "business" && <BusinessInfoTab />}
        {tab === "financial" && <FinancialTab />}
        {tab === "account" && <AccountSettingsTab />}
      </div>
    </div>
  );
}
