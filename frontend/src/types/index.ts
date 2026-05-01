/**
 * 백엔드 도메인 모델(SQLAlchemy) + Pydantic 스키마를 기반으로 정의한
 * 프론트엔드 공통 인터페이스.
 *
 * 출처 매핑
 *  - 인증:      backend/src/app/domains/auth/{model,schema}.py
 *  - 사업장:    backend/src/app/domains/business/{model,schema}.py
 *  - 정책:      backend/src/app/domains/policy/{model,schema}.py
 *  - 진단:      backend/src/app/domains/diagnosis/{model,schema}.py
 *  - 채팅:      backend/src/app/domains/chat/{model,schema}.py
 *  - 비즈픽:    backend/src/app/domains/biz_pick/schema.py
 *  - 알림:      backend/src/app/domains/notification/schema.py
 *  - 공통응답:  backend/src/app/core/response.py  → { status, data, message }
 *
 * 규칙
 *  - 백엔드 Pydantic 필드명을 그대로 사용 (snake_case 유지) — 매핑 실수를 줄임
 *  - UUID/datetime 은 모두 string (ISO 8601) 로 수신
 *  - Enum 은 as const 오브젝트 + union 타입으로 정의 (런타임 & 타입 동시 제공)
 */

// ────────────────────────────────────────────────────────────────────
// 0. 공통 API Envelope
// ────────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  status: number;
  data: T;
  message?: string;
}

export interface ApiError {
  status: number;
  message: string;
  code?: string;
  detail?: unknown;
}

export interface Paginated<T> {
  items: T[];
  total_count: number;
  total_pages: number;
}

// ────────────────────────────────────────────────────────────────────
// 1. 인증 / 사용자 (auth)
// ────────────────────────────────────────────────────────────────────

export const SocialProvider = {
  KAKAO: "KAKAO",
  NAVER: "NAVER",
} as const;
export type SocialProvider = (typeof SocialProvider)[keyof typeof SocialProvider];

export const MilitaryService = {
  COMPLETED: "COMPLETED",
  EXEMPTED: "EXEMPTED",
  IN_PROGRESS: "IN_PROGRESS",
  NA: "NA",
} as const;
export type MilitaryService =
  (typeof MilitaryService)[keyof typeof MilitaryService];

export interface SocialAuthRequest {
  access_token: string;
  provider: SocialProvider;
  device_type: "WEB" | "IOS" | "ANDROID";
}

export interface KakaoCallbackRequest {
  code: string;
  redirect_uri: string;
}

export interface NaverCallbackRequest {
  code: string;
  state: string;
}

export interface SocialLoginResponseData {
  access_token: string;
  refresh_token: string;
  user_id: string;
  name: string;
  is_new_user: boolean;
}

export interface RefreshTokenResponseData {
  access_token: string;
}

export interface MyProfile {
  user_id: string;
  name: string;
  email: string;
  profile_image: string | null;
  interest_sectors: string[];
  is_profile_completed: boolean;
}

export interface ProfilePatchRequest {
  military_service?: MilitaryService | null;
  interest_sectors?: string[] | null;
  is_non_major?: boolean | null;
  tech_stack?: string[] | null;
}

// ────────────────────────────────────────────────────────────────────
// 2. 사업장 / 재무 / 서류 (business)
// ────────────────────────────────────────────────────────────────────

export const FundingPurpose = {
  FACILITY: "FACILITY",
  OPERATING: "OPERATING",
  WORKING: "WORKING",
  MIXED: "MIXED",
  UNSURE: "UNSURE",
} as const;
export type FundingPurpose =
  (typeof FundingPurpose)[keyof typeof FundingPurpose];

export interface BusinessInfo {
  biz_id: string;
  biz_name: string;
  biz_no: string | null;
  representative_name: string | null;
  region_sido: string | null;
  region_sigungu: string | null;
  establishment_date: string | null; // ISO date
  ksic_code: string | null;
  ksic_name: string | null;
  sector_code: string | null;
  is_biz_no_verified: boolean;
  employee_count: number | null;
  funding_purpose: string | null;
  has_tax_arrears: boolean;
  has_patent: boolean;
  is_female_ent: boolean;
  is_ventured: boolean;
  profile_score: number; // 0~100
  created_at: string; // ISO datetime
}

export interface OnboardingRegisterRequest {
  biz_name: string;
  biz_no: string; // 10자리 숫자 또는 "000-00-00000"
  representative_name?: string | null;
  ksic_code: string;
  ksic_name: string;
  sector_code?: string | null;
  region_sido?: string | null;
  region_sigungu?: string | null;
  establishment_date: string; // YYYY-MM-DD
  employee_count: number;
  funding_purpose?: FundingPurpose;
  has_patent?: boolean;
  is_female_ent?: boolean;
  is_ventured?: boolean;
  is_manual?: boolean;
}

export interface OnboardingRegisterResponseData {
  biz_id: string;
  biz_name: string;
  biz_no: string;
  is_manual: boolean;
  profile_score: number;
}

export interface VerifyBizNumberRequest {
  biz_no: string;
}

export interface VerifyBizNumberResponseData {
  is_valid: boolean;
  biz_status: string | null; // 계속사업자 | 휴업자 | 폐업자
  tax_type: string | null;
  error_code: string | null; // TIMEOUT | API_ERROR | NO_DATA | NOT_REGISTERED | SERVER_CONFIG
}

export interface BusinessUpdateRequest {
  biz_name?: string;
  representative_name?: string | null;
  region_sido?: string | null;
  region_sigungu?: string | null;
  establishment_date?: string | null;
  ksic_code?: string | null;
  ksic_name?: string | null;
  sector_code?: string | null;
  employee_count?: number | null;
  funding_purpose?: FundingPurpose | null;
  has_tax_arrears?: boolean;
  has_patent?: boolean;
  is_female_ent?: boolean;
  is_ventured?: boolean;
}

// 재무 스냅샷
export interface FinanceSnapshot {
  finance_id: string;
  snapshot_year: number;
  snapshot_period: "ANNUAL" | "1Q" | "2Q" | "3Q" | "4Q";
  annual_revenue: number | null;
  operating_profit: number | null;
  net_income: number | null;
  total_debt: number | null;
  capital: number | null;
  debt_ratio: number | null;
  employee_count: number | null;
  tax_arrears_yn: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface FinanceCreateRequest {
  snapshot_year: number;
  snapshot_period?: "ANNUAL" | "1Q" | "2Q" | "3Q" | "4Q";
  term_type?: "ANNUAL" | "QUARTERLY";
  annual_revenue?: number | null;
  operating_profit?: number | null;
  net_income?: number | null;
  total_debt?: number | null;
  capital?: number | null;
  employee_count?: number | null;
  tax_arrears_yn?: boolean;
}

export type FinanceUpdateRequest = Partial<
  Omit<FinanceCreateRequest, "snapshot_year" | "snapshot_period" | "term_type">
>;

// 서류 (documents)
export const OcrStatus = {
  PENDING: "PENDING",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
} as const;
export type OcrStatus = (typeof OcrStatus)[keyof typeof OcrStatus];

export interface DocumentListItem {
  document_id: string;
  doc_type: string;
  ocr_status: OcrStatus;
  created_at: string;
}

export interface DocumentDetail {
  document_id: string;
  doc_type: string;
  file_url: string;
  ocr_status: OcrStatus;
  ocr_result: Record<string, unknown> | null;
  issued_at: string | null;
  created_at: string;
}

// 신청 이력 (applications)
export const ApplicationStatus = {
  INTERESTED: "INTERESTED",
  SUBMITTED: "SUBMITTED",
  APPROVED: "APPROVED",
  REJECTED: "REJECTED",
} as const;
export type ApplicationStatus =
  (typeof ApplicationStatus)[keyof typeof ApplicationStatus];

export interface ApplicationItem {
  application_id: string;
  business_id: string;
  policy_id: string;
  policy_title: string;
  status: ApplicationStatus;
  applied_at: string | null;
  updated_at: string;
  memo: string | null;
}

// ────────────────────────────────────────────────────────────────────
// 3. 정책 (policy)
// ────────────────────────────────────────────────────────────────────

export const PolicyStatus = {
  PREPARING: "PREPARING",
  RECRUITING: "RECRUITING",
  CLOSED: "CLOSED",
  END_OF_BUDGET: "END_OF_BUDGET",
} as const;
export type PolicyStatus = (typeof PolicyStatus)[keyof typeof PolicyStatus];

export const MatchLevel = {
  GREEN: "GREEN",
  YELLOW: "YELLOW",
  RED: "RED",
} as const;
export type MatchLevel = (typeof MatchLevel)[keyof typeof MatchLevel];

/** 정책 목록 아이템 (GET /policies) */
export interface PolicyListItem {
  policy_id: string;
  title: string;
  category: string | null;
  closed_at: string; // ISO date (상시접수 = "9999-12-31")
  is_bookmarked: boolean;
}

/** 정책 추천 아이템 (GET /policies/recommend) — 신호등 포함 */
export interface PolicyRecommendItem {
  policy_id: string;
  title: string;
  match_level: MatchLevel;
  match_score: number; // 0~100
  reason: string;
  estimated_probability: number | null; // L2 입력 시에만 제공되는 추정 확률 (0~100)
  is_bookmarked: boolean;
}

/** GET /policies/recommend 응답 본문 */
export interface PolicyRecommendListData {
  items: PolicyRecommendItem[];
  completeness_tier: "L1" | "L2";
  upgrade_hint: string | null; // L1일 때 L2 유도 안내 문구
  missing_fields: string[];
  unverified_notice: string | null;
}

/** 정책 상세 (GET /policies/{id}) */
export interface PolicyDetail {
  policy_id: string;
  title: string;
  content: string;
  support_amount: string | null;
  apply_url: string | null;
  required_documents: string[];
  category: string | null;
  agency_name: string;
  closed_at: string; // ISO date
  view_count: number;
  is_bookmarked: boolean;
}

/** 정책 검색 파라미터 */
export interface PolicySearchParams {
  keyword?: string;
  region?: string;
  category?: string;
  page?: number;
  size?: number;
}

export interface BookmarkToggleResponse {
  is_bookmarked: boolean;
  policy_id: string;
}

// ────────────────────────────────────────────────────────────────────
// 4. 진단 & 시뮬레이션 (diagnosis)
// ────────────────────────────────────────────────────────────────────

export interface SnapshotData {
  revenue: number | null;
  total_debt: number | null;
  employee_count: number | null;
  biz_sector: string | null;
}

export interface PrepareDiagnosisResponse {
  current_snapshot: SnapshotData;
  missing_fields: string[];
  message: string;
  suggest_nts_reverification: boolean;
}

/** POST /diagnoses 의 final_inputs (백엔드 DiagnosisFinalInputs) */
export interface DiagnosisFinalInputs {
  has_tax_arrears: boolean;
  annual_revenue: number | null;
  total_debt: number | null;
  debt_ratio: number | null;
  employee_count: number;
  has_patent: boolean;
  is_female_ent: boolean;
  is_ventured: boolean;
}

export interface ExecuteDiagnosisRequest {
  year: number;
  use_ai_analysis: boolean;
  final_inputs: DiagnosisFinalInputs;
}

export interface ExecuteDiagnosisResponse {
  diagnosis_id: string;
  total_score: number;
  grade: string;
  created_at: string;
  traffic_light: "RED" | "YELLOW" | "GREEN";
}

export interface DiagnosisScores {
  financial_health: number;
  growth_potential: number;
  operational_stability: number;
  risk_management: number;
}

export interface DiagnosisDetail {
  diagnosis_id: string;
  total_score: number;
  grade: string;
  traffic_light: "RED" | "YELLOW" | "GREEN";
  scores: DiagnosisScores;
  summary: string;
  strengths: string[];
  risk_signals: string[];
  action_items: string[];
  snapshot: Record<string, unknown>;
}

export interface DiagnosisHistoryItem {
  diagnosis_id: string;
  score: number;
  date: string;
}

export interface ExecuteSimulationRequest {
  policy_id?: string;
  virtual_conditions: Record<string, unknown>;
}

export interface ExecuteSimulationResponse {
  base_rate: number;
  simulated_rate: number;
  gain_factors: string[];
}

// ────────────────────────────────────────────────────────────────────
// 5. AI 채팅 — 비즈몽 (chat) ★ 핵심
// ────────────────────────────────────────────────────────────────────

/** BizMong 에이전트 타입 (backend/src/app/agents/biz_mong/state.py) */
export const AgentType = {
  GREETING: "greeting",   // 인사/잡담
  GENERAL_QA: "general_qa", // 일반 개념 질문
  DIAGNOSIS: "diagnosis", // 정책자금 진단
  SIMULATOR: "simulator", // 가산점/ROI 시뮬레이션
  RAG: "rag", // 정책 검색 (RAG)
  STATS: "stats", // 동종업계 통계
} as const;
export type AgentType = (typeof AgentType)[keyof typeof AgentType];

/** SSE 스트림 이벤트 */
export type SseEvent =
  | { type: "status"; text: string }
  | { type: "token"; content: string }
  | { type: "done"; agent_type: AgentType; message_id: string; content: string;
      diagnosis_report: AgentDiagnosisReport | null;
      simulation_report: AgentSimulationReport | null;
      stats_insight: AgentStatsInsight | null;
      rag_results: AgentRagResult[] | null; };

export const ChatRole = {
  USER: "user",
  ASSISTANT: "assistant",
  SYSTEM: "system",
} as const;
export type ChatRole = (typeof ChatRole)[keyof typeof ChatRole];

export interface ChatSession {
  session_id: string;
  title: string;
  last_message?: string;
  updated_at: string;
}

export interface CreateSessionRequest {
  initial_message: string;
}

export interface CreateSessionResponseData {
  session_id: string;
  title: string;
  created_at: string;
}

export interface ReferencedPolicy {
  id: string;
  title: string;
}

/** 채팅 로그 (개별 메시지) */
export interface ChatMessage {
  message_id: string;
  role: ChatRole;
  content: string;
  referenced_policies: ReferencedPolicy[];
  created_at: string;
}

export interface SendMessageRequest {
  message: string;
}

export interface AgentCtaEventRequest {
  assistant_message_id: string;
  cta_type: string;
  target_path: string;
  ref_policy_id?: string | null;
  metadata?: Record<string, unknown>;
}

// ── 에이전트 결과 카드 페이로드 (/chat 화면 렌더용) ──
// .cursorrules P07 UI 스펙 기반 — chat_logs.referenced_chunks 또는 별도 result payload 로 수신

export interface DiagnosisResultCard {
  agent_type: typeof AgentType.DIAGNOSIS;
  total_score: number; // 0~100
  scores: DiagnosisScores;
  top_recommendation: {
    policy_id: string;
    title: string;
    score: number;
    reason: string;
  };
  matched_policies: Array<{
    rank: number;
    policy_id: string;
    title: string;
    agency_name: string;
    region: string;
    max_support: number | null;
    closed_at: string;
    score: number;
  }>;
  advice: string;
}

export interface SimulatorResultCard {
  agent_type: typeof AgentType.SIMULATOR;
  virtual_conditions: Record<string, unknown>;
  before_score: number;
  after_score: number;
  diff: number; // after - before
  benefit_amount: number | null; // 연간 이자 절감액 등
  insights: string[];
}

export interface RagResultCard {
  agent_type: typeof AgentType.RAG;
  answer: string;
  references: Array<{
    policy_id: string;
    title: string;
    excerpt: string;
  }>;
}

export interface StatsResultCard {
  agent_type: typeof AgentType.STATS;
  sector_code: string;
  sample_size: number;
  comparisons: Array<{
    metric: "revenue" | "employee_count" | "debt_ratio";
    label: string;
    my_value: number;
    peer_avg: number;
    percentile: number; // 0~100
  }>;
  narrative: string;
}

export type AgentResultCard =
  | DiagnosisResultCard
  | SimulatorResultCard
  | RagResultCard
  | StatsResultCard;

/**
 * 백엔드 /chats/sessions/{id}/agent-message 응답 스키마.
 * (backend/src/app/api/v1/chat_router.py AgentMessageResponse 매핑)
 */
export interface AgentDiagnosisReport {
  score: number;
  top_policy: string;
  advice: string;
  total_candidates: number;
}
export interface AgentSimulationReport {
  original_score: number;
  virtual_score: number;
  diff: number;
  insights: string[];
}
export interface AgentStatsInsight {
  peer_comparison: string;
  market_trend: string;
}
export interface AgentRagResult {
  policy_id?: string;
  title?: string;
  content?: string;
  excerpt?: string;
}

export interface AgentMessageResponse {
  session_id: string;
  message_id: string;
  role: "assistant";
  content: string;
  agent_type: AgentType;
  diagnosis_report: AgentDiagnosisReport | null;
  simulation_report: AgentSimulationReport | null;
  stats_insight: AgentStatsInsight | null;
  rag_results: AgentRagResult[] | null;
  created_at: string;
}

/** 채팅 화면 렌더링 전용 메시지 유니온 타입 */
export type ChatDisplayMessage =
  | { kind: "user"; id: string; content: string; created_at: string }
  | {
      kind: "agent";
      id: string;
      content: string;
      /** 스트리밍 중에는 undefined, 완료 후 확정 */
      agent_type: AgentType | undefined;
      diagnosis_report: AgentDiagnosisReport | null;
      simulation_report: AgentSimulationReport | null;
      stats_insight: AgentStatsInsight | null;
      rag_results: AgentRagResult[] | null;
      created_at: string;
    }
  | { kind: "loading" };

// ────────────────────────────────────────────────────────────────────
// 6. 비즈-픽 (biz_pick)
// ────────────────────────────────────────────────────────────────────

export interface BizPickListItem {
  content_id: string;
  title: string;
  thumbnail_url: string | null;
  category: string;
  view_count: number;
  like_count: number;
  is_liked: boolean;
  created_at: string;
}

export interface BizPickDetail {
  content_id: string;
  title: string;
  body_html: string;
  author: string;
  view_count: number;
  like_count: number;
  is_liked: boolean;
  related_policies: Array<{ id: string; title: string }>;
  tags: string[];
}

export interface BizPickLikeResponse {
  is_liked: boolean;
  total_likes: number;
}

export interface CategoryItem {
  code: string;
  name: string;
}

// ────────────────────────────────────────────────────────────────────
// 7. 알림 (notification)
// ────────────────────────────────────────────────────────────────────

export const NotificationType = {
  POLICY_MATCH: "POLICY_MATCH",
  CHAT_ANSWER: "CHAT_ANSWER",
  DEADLINE: "DEADLINE",
  SYSTEM: "SYSTEM",
} as const;
export type NotificationType =
  (typeof NotificationType)[keyof typeof NotificationType];

export interface NotificationItem {
  noti_id: string;
  type: NotificationType | string;
  title: string;
  content: string;
  is_read: boolean;
  deep_link: string | null;
  created_at: string;
}

export interface NotificationSettings {
  push_enabled: boolean;
  marketing_enabled: boolean;
  policy_update_enabled: boolean;
  chat_answer_enabled: boolean;
}

export type UpdateNotificationSettingsRequest = Partial<NotificationSettings>;

// ────────────────────────────────────────────────────────────────────
// 8. UI 공용 Props (.cursorrules §3)
// ────────────────────────────────────────────────────────────────────

export interface PolicyCardProps {
  policyId: string;
  title: string;
  agencyName: string;
  maxSupport: number | null;
  region: string;
  endDate: string; // ISO 8601
  score?: number;
  trafficLight?: "green" | "yellow" | "red";
  isBookmarked: boolean;
  onBookmark: () => void;
}

export interface ScoreGaugeProps {
  score: number; // 0~100
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export interface TrafficLightBadgeProps {
  status: "green" | "yellow" | "red";
  label?: string;
}

export interface ScoreChangeBadgeProps {
  diff: number;
}

// ────────────────────────────────────────────────────────────────────
// 9. 관리자 (admin) — PAGE 12: 통합 관리 센터
// ────────────────────────────────────────────────────────────────────
/**
 * 관리자 도메인은 일반 사용자 API(api-client.ts)와 분리된 별도 axios
 * 인스턴스(admin-api-client.ts)를 사용한다. 모든 요청에 Authorization:
 * Bearer {adminToken} 첨부가 필요하며, 401/403 시 /admin/login 으로
 * 리다이렉트한다.
 */

export interface AdminLoginRequest {
  login_id: string;
  password: string;
}

export interface AdminLoginResponse {
  admin_token: string;
  admin_id: string;
  name: string;
  role: "SUPER_ADMIN" | "OPERATOR" | string;
  expires_at: string;
}

// ── 9-1. 대시보드 통계 ────────────────────────────────────────────

export interface DashboardStats {
  new_users_today: number;
  active_chats_today: number;
  popular_policies: Array<{
    policy_id: string;
    title: string;
    view_count: number;
  }>;
  /** 시스템 신호등 요약 (optional — /admin/monitoring/health 중복) */
  system_status?: SystemHealthStatus;
}

// ── 9-2. 유저 관리 ────────────────────────────────────────────────

export interface AdminUserItem {
  user_id: string;
  name: string;
  email: string;
  status: "ACTIVE" | "INACTIVE" | "SUSPENDED" | string;
  is_active: boolean;
  provider?: string;
  biz_count?: number;
  created_at: string;
  last_login_at?: string | null;
}

export interface AdminUsersParams {
  page?: number;
  size?: number;
  search_keyword?: string;
  include_inactive_users?: boolean;
}

// ── 9-3. 채팅 모니터링 ────────────────────────────────────────────

export interface ChatMonitorItem {
  session_id: string;
  user_id: string;
  user_name?: string;
  user_msg: string;
  ai_res: string;
  agent_type?: AgentType | string | null;
  timestamp: string;
}

export interface AdminChatLogsParams {
  user_id?: string;
  page?: number;
  size?: number;
}

// ── 9-4. 감사 로그 (데이터 수정 이력) ────────────────────────────

export interface AuditLogItem {
  audit_id: string;
  admin_id: string;
  admin_name?: string;
  action: string;
  target: string;
  target_id?: string | null;
  diff?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at: string;
}

// ── 9-5. 배치 작업 현황 ──────────────────────────────────────────

export const BatchStatus = {
  SUCCESS: "SUCCESS",
  RUNNING: "RUNNING",
  FAILED: "FAILED",
  PENDING: "PENDING",
  SCHEDULED: "SCHEDULED",
} as const;
export type BatchStatus = (typeof BatchStatus)[keyof typeof BatchStatus];

export interface BatchStatusItem {
  job_id: string;
  job_name: string;
  last_run: string | null;
  next_run?: string | null;
  status: BatchStatus | string;
  total_count?: number | null;
  processed_count?: number | null;
  success_count?: number | null;
  fail_count?: number | null;
  duration_ms?: number | null;
}

export interface BatchLogDetail {
  job_id: string;
  raw_log: string;
}

// ── 9-6. 정책 관리 (관리자 CRUD + 수집 트리거) ───────────────────

export interface AdminPolicyCreateRequest {
  title: string;
  content: string;
  category?: string | null;
  agency_name: string;
  support_amount?: string | null;
  apply_url?: string | null;
  required_documents?: string[];
  closed_at?: string | null;
  status?: PolicyStatus;
}

export type AdminPolicyUpdateRequest = Partial<AdminPolicyCreateRequest>;

export interface PolicySyncRunParams {
  page_start?: number;
  page_end?: number;
  rows_per_page?: number;
  with_ai?: boolean;
  date_from?: string;
  date_to?: string;
}

export interface PolicySyncResult {
  inserted: number;
  updated: number;
  skipped: number;
  failed: number;
  total_processed: number;
  elapsed_ms?: number;
  message?: string;
}

export interface PolicyEmbedResult {
  embedded: number;
  remaining: number;
  elapsed_ms?: number;
  message?: string;
}

// ── 9-7. 비즈픽 콘텐츠 관리 ──────────────────────────────────────

export interface BizPickContentCreateRequest {
  title: string;
  body_html: string;
  thumbnail_url?: string | null;
  category: string;
  tags?: string[];
  related_policy_ids?: string[];
  is_published?: boolean;
  scheduled_at?: string | null;
}

export type BizPickContentUpdateRequest = Partial<BizPickContentCreateRequest>;

export interface BizPickContentListItem extends BizPickListItem {
  is_published: boolean;
  scheduled_at?: string | null;
  updated_at: string;
}

// AI 카드뉴스 생성 — 정책 URL → 3줄 요약 + 카드 초안
export interface AiCardNewsGenerateRequest {
  policy_url?: string;
  policy_id?: string;
  raw_text?: string;
}

export interface AiCardNewsGenerateResponse {
  suggested_title: string;
  three_line_summary: string[];
  body_html: string;
  suggested_category: string;
  suggested_tags: string[];
  suggested_thumbnail_url?: string | null;
}

// AI 연관 정책 추천
export interface AiRelatedPoliciesRequest {
  content_body: string;
  limit?: number;
}

export interface AiRelatedPoliciesResponse {
  items: Array<{
    policy_id: string;
    title: string;
    reason: string;
    score: number;
  }>;
}

// ── 9-8. 로직 디버깅 / 피드백 센터 ───────────────────────────────

export const FeedbackReason = {
  INFO_WRONG: "INFO_WRONG", // 정보 오류
  NOT_APPLICABLE: "NOT_APPLICABLE", // 실제 상황과 다름
  DIFFICULT_TERM: "DIFFICULT_TERM", // 용어 어려움
  OTHER: "OTHER",
} as const;
export type FeedbackReason =
  (typeof FeedbackReason)[keyof typeof FeedbackReason];

export interface FeedbackItem {
  feedback_id: string;
  session_id: string;
  message_id: string;
  user_id: string;
  user_name?: string;
  reason: FeedbackReason | string;
  reason_label: string;
  user_comment?: string | null;
  ai_response_snippet: string;
  created_at: string;
  is_resolved: boolean;
}

export interface FeedbackListParams {
  reason?: FeedbackReason;
  is_resolved?: boolean;
  page?: number;
  size?: number;
}

export interface FeedbackContextDetail {
  feedback: FeedbackItem;
  conversation: ChatMessage[];
  matching_logic_snapshot: {
    applied_at: string;
    rules: Array<{ rule_id: string; description: string; weight: number }>;
    matched_policies: Array<{
      policy_id: string;
      title: string;
      score: number;
    }>;
    raw_payload?: Record<string, unknown>;
  };
}

export interface CorrectionNoteRequest {
  feedback_id: string;
  question_pattern: string;
  expected_answer: string;
  applies_to_agent?: AgentType | "ALL";
  is_active?: boolean;
}

export interface CorrectionNoteItem {
  note_id: string;
  feedback_id: string;
  question_pattern: string;
  expected_answer: string;
  applies_to_agent: AgentType | "ALL" | string;
  is_active: boolean;
  created_by: string;
  created_at: string;
}

// ── 9-9. 시스템 건강 & 비용 모니터링 ─────────────────────────────

export const SystemHealth = {
  HEALTHY: "HEALTHY",
  DEGRADED: "DEGRADED",
  DOWN: "DOWN",
} as const;
export type SystemHealth = (typeof SystemHealth)[keyof typeof SystemHealth];

export interface SystemHealthStatus {
  status: SystemHealth | string;
  latency_p50_ms: number;
  latency_p95_ms: number;
  error_rate_pct: number;
  uptime_pct: number;
  last_incident_at?: string | null;
  components?: Array<{
    name: string;
    status: SystemHealth | string;
    message?: string;
  }>;
}

export type MonitoringRange = "1h" | "24h" | "7d" | "30d";

export interface AgentMonitoringFilters {
  intent?: string;
  model?: string;
  fallback?: boolean;
  status?: string;
}

export interface LatencyTimeSeriesPoint {
  timestamp: string;
  p50_ms: number;
  p95_ms: number;
  count: number;
  error_rate_pct: number;
}

export interface LatencyTimeSeries {
  range: MonitoringRange;
  points: LatencyTimeSeriesPoint[];
}

export interface TokenCostSummary {
  date: string;
  total_usd: number;
  total_krw: number;
  total_tokens_in: number;
  total_tokens_out: number;
  by_model: Array<{
    model: string;
    tokens_in: number;
    tokens_out: number;
    cost_usd: number;
    cost_krw: number;
  }>;
}

export interface AgentMonitoringOverview {
  range: MonitoringRange;
  filters?: AgentMonitoringFilters;
  total_runs: number;
  success_rate_pct: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_usd: number;
  total_cost_krw: number;
  fallback_runs: number;
  cta_clicks: number;
  dislike_feedback_count: number;
  quality_metrics?: {
    fallback_rate_pct: number;
    dislike_feedback_rate_pct: number;
  };
  by_intent: Array<{
    intent: string;
    runs: number;
    avg_latency_ms: number;
    cost_usd: number;
    error_rate_pct: number;
  }>;
  by_model: Array<{
    model: string;
    runs: number;
    tokens_in: number;
    tokens_out: number;
    cost_usd: number;
  }>;
  by_prompt_version: Array<{
    version: string;
    runs: number;
    avg_latency_ms: number;
    cost_usd: number;
  }>;
  by_graph_version: Array<{
    version: string;
    runs: number;
    avg_latency_ms: number;
    cost_usd: number;
  }>;
  by_rag_strategy_version: Array<{
    version: string;
    runs: number;
    avg_latency_ms: number;
    cost_usd: number;
  }>;
}

export interface AgentNodeMetricItem {
  node_name: string;
  executions: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  error_count: number;
  error_rate_pct: number;
}

export interface AgentNodeMetricsResponse {
  range: MonitoringRange;
  filters?: AgentMonitoringFilters;
  items: AgentNodeMetricItem[];
}

export interface AgentRunItem {
  run_id: string;
  session_id: string;
  route_intent: string | null;
  final_agent: string | null;
  status: string;
  question_preview: string | null;
  total_latency_ms: number | null;
  first_token_latency_ms: number | null;
  tokens_in: number | null;
  tokens_out: number | null;
  total_cost_usd: number;
  fallback_mode: string | null;
  rag_hit_count: number | null;
  prompt_version: string | null;
  model_name: string | null;
  created_at: string | null;
}

export interface AgentRunListResponse extends Paginated<AgentRunItem> {
  filters?: AgentMonitoringFilters;
}

export interface AgentRunDetailNode {
  node_name: string;
  sequence: number;
  status: string;
  model_name: string | null;
  latency_ms: number | null;
  tokens_in: number | null;
  tokens_out: number | null;
  cost_usd: number;
  error_code: string | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
}

export interface AgentCtaEventItem {
  cta_type: string;
  target_path: string;
  ref_policy_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

export interface AgentRunDetailResponse {
  run: AgentRunItem & {
    fallback_reason: string | null;
    graph_version: string | null;
    rag_strategy_version: string | null;
    error_code: string | null;
    error_message: string | null;
  };
  nodes: AgentRunDetailNode[];
  cta_events: AgentCtaEventItem[];
}

// ── 9-10. 비즈니스 인사이트 ──────────────────────────────────────

export interface UnmetDemandKeyword {
  keyword: string;
  query_count: number;
  last_asked_at: string;
  related_sector_codes?: string[];
}

export interface UnmetDemandResponse {
  items: UnmetDemandKeyword[];
  total_count: number;
  total_pages: number;
}

export interface ConversionStats {
  period: { from: string; to: string };
  consultation_bookings: number;
  solution_clicks: Array<{
    solution_key: string;
    solution_label: string;
    clicks: number;
    conversions: number;
    conversion_rate_pct: number;
  }>;
  revenue_estimate_krw?: number;
}
