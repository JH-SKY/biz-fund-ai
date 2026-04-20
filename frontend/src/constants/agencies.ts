import type { SelectOption } from "@/components/ui/select";

/**
 * 시행 기관(agency) 대표 선택지. 백엔드가 전체 목록 API 를 제공하기 전까지 하드코딩.
 */
export const AGENCY_OPTIONS: SelectOption[] = [
  { value: "", label: "전체 기관" },
  { value: "중소벤처기업부", label: "중소벤처기업부" },
  { value: "소상공인시장진흥공단", label: "소상공인시장진흥공단" },
  { value: "중소벤처기업진흥공단", label: "중소벤처기업진흥공단" },
  { value: "신용보증기금", label: "신용보증기금" },
  { value: "기술보증기금", label: "기술보증기금" },
  { value: "고용노동부", label: "고용노동부" },
  { value: "산업통상자원부", label: "산업통상자원부" },
  { value: "서울특별시", label: "서울특별시" },
  { value: "경기도", label: "경기도" },
  { value: "부산광역시", label: "부산광역시" },
];

export const POLICY_CATEGORIES: SelectOption[] = [
  { value: "", label: "전체 카테고리" },
  { value: "융자", label: "융자" },
  { value: "보조금", label: "보조금" },
  { value: "보증", label: "보증" },
  { value: "R&D", label: "R&D" },
  { value: "인력/고용", label: "인력/고용" },
  { value: "바우처", label: "바우처" },
  { value: "컨설팅", label: "컨설팅" },
];
