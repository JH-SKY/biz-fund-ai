"use client";

/**
 * OnboardingForm — 신규 유저 최초 정보 수집 폼.
 *
 * 입력 필드 (기획서 §2)
 *  - 사업자등록번호: 10자리 숫자 + 하이픈 자동 포맷 (123-45-67890)
 *  - 업종: IndustryCombobox 자동완성
 *  - 상시 근로자 수: 숫자 (0 이상 허용)
 *
 * 유효성
 *  - 실시간: 사업자번호 형식 불일치 시 FieldHint(error) 노출
 *  - 제출: 모든 필드 필수. 통과 시 /api/v1/onboarding/register 호출(TODO) → /dashboard 이동
 */

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label, FieldHint } from "@/components/ui/label";
import { IndustryCombobox } from "./IndustryCombobox";

/** 10자리 숫자로 정규화 */
function normalizeBizNo(v: string): string {
  return v.replace(/\D/g, "").slice(0, 10);
}

/** 입력값에 하이픈 자동 삽입 (123-45-67890) */
function formatBizNo(v: string): string {
  const d = normalizeBizNo(v);
  if (d.length < 4) return d;
  if (d.length < 6) return `${d.slice(0, 3)}-${d.slice(3)}`;
  return `${d.slice(0, 3)}-${d.slice(3, 5)}-${d.slice(5)}`;
}

function isValidBizNo(v: string): boolean {
  return /^\d{10}$/.test(normalizeBizNo(v));
}

export function OnboardingForm() {
  const router = useRouter();

  const [bizNo, setBizNo] = useState("");
  const [industry, setIndustry] = useState("");
  const [employeeCount, setEmployeeCount] = useState<string>("");

  const [touched, setTouched] = useState({
    bizNo: false,
    industry: false,
    employeeCount: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const bizNoError = useMemo(() => {
    if (!touched.bizNo) return null;
    if (!bizNo) return "사업자번호를 입력해주세요.";
    if (!isValidBizNo(bizNo)) return "올바른 사업자번호를 입력해주세요. (10자리 숫자)";
    return null;
  }, [bizNo, touched.bizNo]);

  const industryError =
    touched.industry && !industry ? "업종을 선택해주세요." : null;

  const employeeError = (() => {
    if (!touched.employeeCount) return null;
    if (employeeCount === "") return "근로자 수를 입력해주세요. (0명 입력 가능)";
    const n = Number(employeeCount);
    if (!Number.isFinite(n) || n < 0 || !Number.isInteger(n))
      return "0 이상의 정수로 입력해주세요.";
    return null;
  })();

  const isValid =
    isValidBizNo(bizNo) &&
    !!industry &&
    employeeCount !== "" &&
    Number(employeeCount) >= 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched({ bizNo: true, industry: true, employeeCount: true });
    if (!isValid) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      // TODO(API 연동):
      // await apiClient.post<OnboardingRegisterResponseData>(
      //   "/onboarding/register",
      //   {
      //     biz_no: normalizeBizNo(bizNo),
      //     sector_code: industry,
      //     employee_count: Number(employeeCount),
      //     // biz_name 등은 다음 단계에서 국세청 검증 후 수집 예정
      //   } satisfies OnboardingRegisterRequest
      // );
      await new Promise((r) => setTimeout(r, 700));
      router.push("/dashboard");
    } catch {
      setSubmitError("정보 저장에 실패했어요. 잠시 후 다시 시도해주세요.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* 사업자번호 */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-biz-no" required>
          사업자등록번호
        </Label>
        <Input
          id="ob-biz-no"
          inputMode="numeric"
          autoComplete="off"
          placeholder="123-45-67890"
          value={bizNo}
          onChange={(e) => setBizNo(formatBizNo(e.target.value))}
          onBlur={() => setTouched((t) => ({ ...t, bizNo: true }))}
          invalid={!!bizNoError}
        />
        {bizNoError ? (
          <FieldHint tone="error">{bizNoError}</FieldHint>
        ) : (
          <FieldHint>하이픈은 자동으로 입력됩니다.</FieldHint>
        )}
      </div>

      {/* 업종 */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-industry" required>
          업종
        </Label>
        <IndustryCombobox
          id="ob-industry"
          value={industry}
          onChange={(code) => {
            setIndustry(code);
            setTouched((t) => ({ ...t, industry: true }));
          }}
          invalid={!!industryError}
        />
        {industryError ? (
          <FieldHint tone="error">{industryError}</FieldHint>
        ) : (
          <FieldHint>키워드를 입력하면 자동으로 검색돼요.</FieldHint>
        )}
      </div>

      {/* 상시 근로자 수 */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-employee" required>
          상시 근로자 수
        </Label>
        <Input
          id="ob-employee"
          type="number"
          inputMode="numeric"
          min={0}
          step={1}
          placeholder="본인 제외, 0명 입력 가능"
          value={employeeCount}
          onChange={(e) => setEmployeeCount(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, employeeCount: true }))}
          invalid={!!employeeError}
          rightIcon={<span className="text-xs">명</span>}
        />
        {employeeError && <FieldHint tone="error">{employeeError}</FieldHint>}
      </div>

      {submitError && (
        <div
          role="alert"
          className="rounded-lg bg-danger-50 px-3 py-2 text-sm text-danger-600"
        >
          {submitError}
        </div>
      )}

      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="w-full"
        loading={submitting}
        disabled={!isValid || submitting}
      >
        분석 결과 확인하기
        {!submitting && <ArrowRight />}
      </Button>

      <p className="text-center text-xs text-ink-tertiary">
        입력하신 정보는 정책자금 매칭에만 사용되며 외부에 공개되지 않습니다.
      </p>
    </form>
  );
}
