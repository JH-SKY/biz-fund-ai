"use client";

/**
 * [P03] 온보딩 페이지 — `/onboarding`
 *
 * 레이아웃
 *  - ① Sticky Header: 업종 평균 수혜액 강조 문구
 *  - ② Input Form: OnboardingForm
 *
 * TODO(권한 가드)
 *  - 로그인 세션 미확인 시 /login 으로 리다이렉트
 *  - 이미 온보딩 완료한 유저는 /dashboard 로 리다이렉트
 */

import { Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OnboardingForm } from "@/features/onboarding/OnboardingForm";

export default function OnboardingPage() {
  // TODO: 로그인 가드 + 온보딩 플래그 확인 후 리다이렉트
  // const { user } = useAuth();
  // useEffect(() => {
  //   if (!user) router.replace("/login");
  //   else if (user.is_profile_completed) router.replace("/dashboard");
  // }, [user]);

  return (
    <div className="w-full max-w-lg">
      {/* ① Sticky Motivation Header */}
      <div className="sticky top-0 z-10 -mx-4 mb-4 rounded-xl bg-accent-50/95 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-2xl sm:px-5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent-600" />
          <p className="text-sm text-accent-700">
            사장님 업종의 평균 수혜액은{" "}
            <span className="font-bold text-accent-800">약 3,200만 원</span>
            입니다.
          </p>
        </div>
      </div>

      {/* ② Form */}
      <Card>
        <CardHeader>
          <p className="text-xs font-semibold uppercase tracking-wider text-primary-600">
            Step 1 / 1 — 간단 정보 입력
          </p>
          <CardTitle className="mt-1 text-2xl">
            사장님, 정확한 분석을 위해
            <br />
            세 가지만 알려주세요 🙌
          </CardTitle>
        </CardHeader>
        <CardContent>
          <OnboardingForm />
        </CardContent>
      </Card>
    </div>
  );
}
