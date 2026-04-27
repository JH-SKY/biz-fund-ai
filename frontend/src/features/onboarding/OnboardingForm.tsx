"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label, FieldHint } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { IndustryCombobox } from "./IndustryCombobox";
import { REGION_OPTIONS, getSigunguOptions } from "@/constants/regions";
import { businessService } from "@/lib/services";
import { useAuthStore } from "@/stores/auth-store";
import { useBusinessStore } from "@/stores/business-store";
import { FundingPurpose } from "@/types";

type FundingPurposeValue = (typeof FundingPurpose)[keyof typeof FundingPurpose];

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
  if (
    result.error_code === "SERVER_CONFIG" ||
    result.error_code === "API_ERROR"
  ) {
    return "사업자번호 확인 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해 주세요.";
  }
  if (
    result.error_code === "NO_DATA" ||
    result.error_code === "NOT_REGISTERED"
  ) {
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
  const user = useAuthStore((state) => state.user);
  const setOnboarded = useAuthStore((state) => state.setOnboarded);
  const setActiveBusiness = useBusinessStore((state) => state.setActiveBusiness);

  const [bizName, setBizName] = useState("");
  const [bizNo, setBizNo] = useState("");
  const [regionSido, setRegionSido] = useState("");
  const [regionSigungu, setRegionSigungu] = useState("");
  const [ksicCode, setKsicCode] = useState("");
  const [ksicName, setKsicName] = useState("");
  const [establishmentDate, setEstablishmentDate] = useState("");
  const [employeeCount, setEmployeeCount] = useState("");
  const [fundingPurpose, setFundingPurpose] = useState<FundingPurposeValue>(
    FundingPurpose.UNSURE
  );
  const [submitPhase, setSubmitPhase] = useState<SubmitPhase>("idle");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [verifySuccessMessage, setVerifySuccessMessage] = useState<string | null>(
    null
  );
  const [allowManualRegistration, setAllowManualRegistration] = useState(false);

  const [touched, setTouched] = useState({
    bizName: false,
    bizNo: false,
    regionSido: false,
    regionSigungu: false,
    industry: false,
    establishmentDate: false,
    employeeCount: false,
    funding: false,
  });

  const sigunguOptions = useMemo(
    () => getSigunguOptions(regionSido),
    [regionSido]
  );

  const bizNameError = useMemo(() => {
    if (!touched.bizName) return null;
    if (!bizName.trim()) return "상호명을 입력해 주세요.";
    if (bizName.trim().length > 100) {
      return "상호명은 100자 이하로 입력해 주세요.";
    }
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

  const regionSidoError = useMemo(() => {
    if (!touched.regionSido) return null;
    if (!regionSido) return "지역(시도)을 선택해 주세요.";
    return null;
  }, [regionSido, touched.regionSido]);

  const regionSigunguError = useMemo(() => {
    if (!touched.regionSigungu) return null;
    if (!regionSigungu) return "시군구를 선택해 주세요.";
    return null;
  }, [regionSigungu, touched.regionSigungu]);

  const industryError = useMemo(() => {
    if (!touched.industry) return null;
    if (!ksicCode || !ksicName) return "검색 후 업종을 선택해 주세요.";
    return null;
  }, [ksicCode, ksicName, touched.industry]);

  const establishmentDateError = useMemo(() => {
    if (!touched.establishmentDate) return null;
    if (!establishmentDate) return "개업일을 선택해 주세요.";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(establishmentDate)) {
      return "올바른 날짜를 선택해 주세요.";
    }
    return null;
  }, [establishmentDate, touched.establishmentDate]);

  const employeeError = useMemo(() => {
    if (!touched.employeeCount) return null;
    if (employeeCount === "") return "상시 근로자 수를 입력해 주세요. (0명 가능)";
    const n = Number(employeeCount);
    if (!Number.isInteger(n) || n < 0) {
      return "0 이상의 정수로 입력해 주세요.";
    }
    return null;
  }, [employeeCount, touched.employeeCount]);

  const isFormValid =
    bizName.trim().length > 0 &&
    bizName.trim().length <= 100 &&
    isValidBizNo(bizNo) &&
    Boolean(regionSido) &&
    Boolean(regionSigungu) &&
    Boolean(ksicCode) &&
    Boolean(ksicName) &&
    /^\d{4}-\d{2}-\d{2}$/.test(establishmentDate) &&
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

  const submitRegistration = async (
    normalizedBizNo: string,
    manualRegistration: boolean
  ) => {
    setSubmitPhase("register");

    const registered = await businessService.registerBusiness({
      biz_name: bizName.trim(),
      biz_no: normalizedBizNo,
      representative_name: user?.name?.trim() || undefined,
      ksic_code: ksicCode,
      ksic_name: ksicName,
      sector_code: ksicCode,
      region_sido: regionSido,
      region_sigungu: regionSigungu,
      establishment_date: establishmentDate,
      employee_count: Number(employeeCount),
      funding_purpose: fundingPurpose,
      is_manual: manualRegistration,
    });

    setOnboarded();
    setActiveBusiness(registered.biz_id, registered.biz_name);
    router.replace("/dashboard");
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched({
      bizName: true,
      bizNo: true,
      regionSido: true,
      regionSigungu: true,
      industry: true,
      establishmentDate: true,
      employeeCount: true,
      funding: true,
    });
    setSubmitError(null);
    setVerifySuccessMessage(null);
    setAllowManualRegistration(false);

    if (!isFormValid) return;

    const normalizedBizNo = normalizeBizNo(bizNo);

    try {
      setSubmitPhase("verify");
      const verifyResult = await businessService.verifyBizNumber({
        biz_no: normalizedBizNo,
      });

      if (!verifyResult.is_valid) {
        if (
          verifyResult.error_code === "TIMEOUT" ||
          verifyResult.error_code === "SERVER_CONFIG" ||
          verifyResult.error_code === "API_ERROR"
        ) {
          setAllowManualRegistration(true);
        }
        setSubmitError(getVerifyFailureMessage(verifyResult));
        return;
      }

      setVerifySuccessMessage(
        "사업자번호 확인이 완료되었습니다. 등록을 계속 진행합니다."
      );
      await submitRegistration(normalizedBizNo, false);
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

  const handleManualRegistration = async () => {
    if (!isFormValid || isSubmitting) return;

    const normalizedBizNo = normalizeBizNo(bizNo);
    setSubmitError(null);
    setVerifySuccessMessage(null);

    try {
      await submitRegistration(normalizedBizNo, true);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "수동 등록을 진행하지 못했습니다. 잠시 후 다시 시도해 주세요.";
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
          <FieldHint>대시보드와 프로필에 표시되는 사업장 이름입니다.</FieldHint>
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
          value={ksicCode}
          onChange={({ code, name }) => {
            setKsicCode(code);
            setKsicName(name);
            setTouched((prev) => ({ ...prev, industry: true }));
          }}
          invalid={Boolean(industryError)}
        />
        {industryError ? (
          <FieldHint tone="error">{industryError}</FieldHint>
        ) : (
          <FieldHint>
            키워드로 검색한 뒤 항목을 선택하면 5자리 KSIC 코드와 표시명이 함께
            전송됩니다.
          </FieldHint>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-open-date" required>
          개업일
        </Label>
        <Input
          id="ob-open-date"
          data-testid="onboarding-establishment-date"
          type="date"
          value={establishmentDate}
          onChange={(e) => setEstablishmentDate(e.target.value)}
          onBlur={() =>
            setTouched((prev) => ({ ...prev, establishmentDate: true }))
          }
          invalid={Boolean(establishmentDateError)}
        />
        {establishmentDateError ? (
          <FieldHint tone="error">{establishmentDateError}</FieldHint>
        ) : (
          <FieldHint>정책 매칭·업력 산정에 사용됩니다.</FieldHint>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-employee" required>
          상시 근로자 수(대략)
        </Label>
        <div className="flex flex-wrap gap-2">
          {(
            [
              { label: "5명 미만", v: 2 },
              { label: "5~9명", v: 7 },
              { label: "10~29명", v: 15 },
              { label: "30명 이상", v: 32 },
            ] as const
          ).map((b) => (
            <Button
              key={b.label}
              type="button"
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => {
                setEmployeeCount(String(b.v));
                setTouched((p) => ({ ...p, employeeCount: true }));
              }}
            >
              {b.label}
            </Button>
          ))}
        </div>
        <Input
          id="ob-employee"
          data-testid="onboarding-employee-count"
          type="number"
          inputMode="numeric"
          min={0}
          step={1}
          placeholder="0"
          value={employeeCount}
          onChange={(e) => setEmployeeCount(e.target.value)}
          onBlur={() => setTouched((p) => ({ ...p, employeeCount: true }))}
          invalid={Boolean(employeeError)}
          rightIcon={<span className="text-xs">명</span>}
        />
        {employeeError ? (
          <FieldHint tone="error">{employeeError}</FieldHint>
        ) : (
          <FieldHint>
            4대보험 상시·대략 인원(본인·일용 제외)을 맞춰주세요. 맞춤
            정책(소상공인/중소) 구분에 쓰입니다.
          </FieldHint>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ob-funding" required>
          주로 필요한 자금 용도
        </Label>
        <Select
          id="ob-funding"
          data-testid="onboarding-funding-purpose"
          value={fundingPurpose}
          onChange={(e) => {
            setFundingPurpose(e.target.value as FundingPurposeValue);
            setTouched((p) => ({ ...p, funding: true }));
          }}
          onBlur={() => setTouched((p) => ({ ...p, funding: true }))}
          options={[
            { value: FundingPurpose.FACILITY, label: "시설·기계·도입" },
            { value: FundingPurpose.OPERATING, label: "운영·인건비" },
            { value: FundingPurpose.WORKING, label: "운전(유동)자금" },
            { value: FundingPurpose.MIXED, label: "복합" },
            { value: FundingPurpose.UNSURE, label: "잘 모르겠어요" },
          ]}
        />
        <FieldHint>추천·큐레이션 분류(시설/운영)에 참고됩니다.</FieldHint>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ob-region-sido" required>
            지역(시도)
          </Label>
          <Select
            id="ob-region-sido"
            value={regionSido}
            onChange={(event) => {
              setRegionSido(event.target.value);
              setRegionSigungu("");
              setTouched((prev) => ({
                ...prev,
                regionSido: true,
                regionSigungu: false,
              }));
            }}
            options={REGION_OPTIONS.filter((region) => region.value !== "ALL")}
            placeholder="시도 선택"
            invalid={Boolean(regionSidoError)}
          />
          {regionSidoError ? (
            <FieldHint tone="error">{regionSidoError}</FieldHint>
          ) : (
            <FieldHint>정책 매칭과 프로필 분석에 쓰이는 기본 지역입니다.</FieldHint>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ob-region-sigungu" required>
            시군구
          </Label>
          <Select
            id="ob-region-sigungu"
            data-testid="onboarding-region-sigungu"
            value={regionSigungu}
            onChange={(event) => setRegionSigungu(event.target.value)}
            onBlur={() =>
              setTouched((prev) => ({ ...prev, regionSigungu: true }))
            }
            invalid={Boolean(regionSigunguError)}
            disabled={!regionSido}
            options={sigunguOptions}
            placeholder={regionSido ? "시군구 선택" : "먼저 시도를 선택해 주세요"}
          />
          {regionSigunguError ? (
            <FieldHint tone="error">{regionSigunguError}</FieldHint>
          ) : (
            <FieldHint>선택한 시도에 맞는 시군구만 고를 수 있습니다.</FieldHint>
          )}
        </div>
      </div>

      {submitError && (
        <div
          role="alert"
          className="rounded-lg bg-danger-50 px-3 py-2 text-sm text-danger-600"
        >
          {submitError}
        </div>
      )}

      {allowManualRegistration && (
        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={handleManualRegistration}
          disabled={isSubmitting}
        >
          수동 등록으로 계속하기
        </Button>
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
