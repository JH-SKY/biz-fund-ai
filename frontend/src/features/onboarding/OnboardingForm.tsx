"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label, FieldHint } from "@/components/ui/label";
import { IndustryCombobox } from "./IndustryCombobox";
import { businessService } from "@/lib/services";
import { useAuthStore } from "@/stores/auth-store";
import { useBusinessStore } from "@/stores/business-store";

type SubmitPhase = "idle" | "verify" | "register";

function normalizeBizNo(value: string): string {
  return value.replace(/\D/g, "").slice(0, 10);
}

function formatBizNo(value: string): string {
  const digits = normalizeBizNo(value);
  if (digits.length < 4) return digits;
  if (digits.length < 6) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 5)}-${digits.slice(5)}`;
}

function isValidBizNo(value: string): boolean {
  return /^\d{10}$/.test(normalizeBizNo(value));
}

function getVerifyFailureMessage(result: {
  is_valid: boolean;
  biz_status: string | null;
  error_code: string | null;
}): string {
  if (result.error_code === "TIMEOUT") {
    return "사업자번호 확인 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.";
  }
  if (result.error_code === "SERVER_CONFIG" || result.error_code === "API_ERROR") {
    return "사업자번호 확인 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해 주세요.";
  }
  if (result.error_code === "NO_DATA" || result.error_code === "NOT_REGISTERED") {
    return "등록된 사업자번호를 찾지 못했습니다. 입력한 번호를 다시 확인해 주세요.";
  }
  if (result.biz_status === "폐업") {
    return "폐업 상태의 사업자는 현재 등록할 수 없습니다.";
  }
  if (result.biz_status === "휴업") {
    return "휴업 상태의 사업자는 현재 등록할 수 없습니다.";
  }
  return "유효한 사업자번호인지 확인하지 못했습니다. 입력값을 다시 확인해 주세요.";
}

export function OnboardingForm() {
  const router = useRouter();
  const setOnboarded = useAuthStore((state) => state.setOnboarded);
  const setActiveBusiness = useBusinessStore((state) => state.setActiveBusiness);

  const [bizName, setBizName] = useState("");
  const [bizNo, setBizNo] = useState("");
  const [industry, setIndustry] = useState("");
  const [employeeCount, setEmployeeCount] = useState("");
  const [submitPhase, setSubmitPhase] = useState<SubmitPhase>("idle");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [verifySuccessMessage, setVerifySuccessMessage] = useState<string | null>(null);

  const [touched, setTouched] = useState({
    bizName: false,
    bizNo: false,
    industry: false,
    employeeCount: false,
  });

  const bizNameError = useMemo(() => {
    if (!touched.bizName) return null;
    if (!bizName.trim()) return "상호명을 입력해 주세요.";
    if (bizName.trim().length > 100) return "상호명은 100자 이하로 입력해 주세요.";
    return null;
  }, [bizName, touched.bizName]);

  const bizNoError = useMemo(() => {
    if (!touched.bizNo) return null;
    if (!bizNo) return "사업자등록번호를 입력해 주세요.";
    if (!isValidBizNo(bizNo)) {
      return "올바른 사업자등록번호를 입력해 주세요. (10자리 숫자)";
    }
    return null;
  }, [bizNo, touched.bizNo]);

  const industryError =
    touched.industry && !industry ? "업종을 선택해 주세요." : null;

  const employeeError = useMemo(() => {
    if (!touched.employeeCount) return null;
    if (employeeCount === "") {
      return "상시 근로자 수를 입력해 주세요. (0명 입력 가능)";
    }
    const count = Number(employeeCount);
    if (!Number.isFinite(count) || count < 0 || !Number.isInteger(count)) {
      return "0 이상의 정수로 입력해 주세요.";
    }
    return null;
  }, [employeeCount, touched.employeeCount]);

  const isFormValid =
    bizName.trim().length > 0 &&
    bizName.trim().length <= 100 &&
    isValidBizNo(bizNo) &&
    Boolean(industry) &&
    employeeCount !== "" &&
    Number.isInteger(Number(employeeCount)) &&
    Number(employeeCount) >= 0;

  const isSubmitting = submitPhase !== "idle";
  const buttonLabel =
    submitPhase === "verify"
      ? "사업자번호 확인 중..."
      : submitPhase === "register"
        ? "사업 정보 등록 중..."
        : "분석 결과 확인하기";

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched({
      bizName: true,
      bizNo: true,
      industry: true,
      employeeCount: true,
    });
    setSubmitError(null);
    setVerifySuccessMessage(null);

    if (!isFormValid) {
      return;
    }

    const normalizedBizNo = normalizeBizNo(bizNo);

    try {
      setSubmitPhase("verify");
      const verifyResult = await businessService.verifyBizNumber({
        biz_no: normalizedBizNo,
      });

      if (!verifyResult.is_valid) {
        setSubmitError(getVerifyFailureMessage(verifyResult));
        return;
      }

      setVerifySuccessMessage("사업자번호 확인이 완료되었습니다. 등록을 계속 진행합니다.");

      setSubmitPhase("register");
      const registered = await businessService.registerBusiness({
        biz_name: bizName.trim(),
        biz_no: normalizedBizNo,
        sector_code: industry,
        employee_count: Number(employeeCount),
      });

      setOnboarded();
      setActiveBusiness(registered.biz_id, registered.biz_name);
      router.replace("/dashboard");
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "온보딩 정보를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.";
      setSubmitError(message);
    } finally {
      setSubmitPhase("idle");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5"
      data-testid="onboarding-form"
    >
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-biz-name" required>
          상호명
        </Label>
        <Input
          id="ob-biz-name"
          data-testid="onboarding-biz-name"
          autoComplete="organization"
          placeholder="예: 비즈업 스튜디오"
          value={bizName}
          onChange={(event) => setBizName(event.target.value)}
          onBlur={() => setTouched((prev) => ({ ...prev, bizName: true }))}
          invalid={Boolean(bizNameError)}
        />
        {bizNameError ? (
          <FieldHint tone="error">{bizNameError}</FieldHint>
        ) : (
          <FieldHint>대시보드와 프로필에 표시될 사업장 이름입니다.</FieldHint>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-biz-no" required>
          사업자등록번호
        </Label>
        <Input
          id="ob-biz-no"
          data-testid="onboarding-biz-no"
          inputMode="numeric"
          autoComplete="off"
          placeholder="123-45-67890"
          value={bizNo}
          onChange={(event) => {
            setBizNo(formatBizNo(event.target.value));
            setVerifySuccessMessage(null);
            setSubmitError(null);
          }}
          onBlur={() => setTouched((prev) => ({ ...prev, bizNo: true }))}
          invalid={Boolean(bizNoError)}
        />
        {bizNoError ? (
          <FieldHint tone="error">{bizNoError}</FieldHint>
        ) : verifySuccessMessage ? (
          <FieldHint tone="success">{verifySuccessMessage}</FieldHint>
        ) : (
          <FieldHint>하이픈은 자동으로 입력됩니다.</FieldHint>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-industry" required>
          업종
        </Label>
        <IndustryCombobox
          id="ob-industry"
          value={industry}
          onChange={(code) => {
            setIndustry(code);
            setTouched((prev) => ({ ...prev, industry: true }));
          }}
          invalid={Boolean(industryError)}
        />
        {industryError ? (
          <FieldHint tone="error">{industryError}</FieldHint>
        ) : (
          <FieldHint>키워드를 입력하면 업종 후보를 바로 찾을 수 있습니다.</FieldHint>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-employee" required>
          상시 근로자 수
        </Label>
        <Input
          id="ob-employee"
          data-testid="onboarding-employee-count"
          type="number"
          inputMode="numeric"
          min={0}
          step={1}
          placeholder="본인 제외, 0명 입력 가능"
          value={employeeCount}
          onChange={(event) => setEmployeeCount(event.target.value)}
          onBlur={() =>
            setTouched((prev) => ({ ...prev, employeeCount: true }))
          }
          invalid={Boolean(employeeError)}
          rightIcon={<span className="text-xs">명</span>}
        />
        {employeeError ? (
          <FieldHint tone="error">{employeeError}</FieldHint>
        ) : (
          <FieldHint>현재 고용 인원은 이후 매칭 정확도 계산에 활용됩니다.</FieldHint>
        )}
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
        data-testid="onboarding-submit"
        size="lg"
        className="w-full"
        loading={isSubmitting}
        disabled={!isFormValid || isSubmitting}
      >
        {buttonLabel}
        {!isSubmitting && <ArrowRight />}
      </Button>

      <p className="text-center text-xs text-ink-tertiary">
        입력하신 정보는 정책자금 분석과 대시보드 초기 설정에만 사용됩니다.
      </p>
    </form>
  );
}
