/**
 * 정밀진단 / 시뮬레이션 전용 React Query 훅.
 *
 *  - usePrepareDiagnosis   : GET /diagnoses/prepare (사전 데이터 로드)
 *  - useExecuteDiagnosis   : POST /diagnoses mutation
 *  - useDiagnosisDetail    : GET /diagnoses/:id
 *  - useExecuteSimulation  : POST /simulations mutation
 *  - useMyFinanceSnapshot  : GET /businesses/finance/history → 최신 스냅샷
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  businessService,
  diagnosisService,
} from "@/lib/services";
import { queryKeys } from "@/lib/query-keys";
import type {
  ExecuteDiagnosisRequest,
  ExecuteSimulationRequest,
  FinanceSnapshot,
} from "@/types";
import { useBusinessStore } from "@/stores/business-store";

// ── 진단 준비 (사전 데이터 로드) ──────────────────────────────────────
export function usePrepareDiagnosis() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: queryKeys.diagnoses.prepare(bizId),
    queryFn: () => diagnosisService.prepare(),
    enabled: Boolean(bizId),
    staleTime: 30 * 1000,
  });
}

// ── 진단 실행 mutation ───────────────────────────────────────────────
export function useExecuteDiagnosis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: ExecuteDiagnosisRequest) => diagnosisService.execute(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.diagnoses.all });
      qc.invalidateQueries({ queryKey: queryKeys.policies.all });
      qc.invalidateQueries({ queryKey: queryKeys.business.me });
      qc.invalidateQueries({ queryKey: ["businesses", "finance"] });
    },
  });
}

// ── 진단 상세 조회 ────────────────────────────────────────────────────
export function useDiagnosisDetail(diagnosisId: string | null) {
  return useQuery({
    queryKey: queryKeys.diagnoses.detail(diagnosisId),
    queryFn: () => diagnosisService.fetchDetail(diagnosisId!),
    enabled: Boolean(diagnosisId),
    staleTime: 5 * 60 * 1000,
  });
}

// ── 시뮬레이션 실행 mutation ──────────────────────────────────────────
export function useExecuteSimulation() {
  return useMutation({
    mutationFn: (req: ExecuteSimulationRequest) =>
      diagnosisService.executeSimulation(req),
  });
}

// ── 최신 재무 스냅샷 (시뮬 페이지 사전 채움용) ──────────────────────
export function useMyFinanceSnapshot() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery<FinanceSnapshot[], unknown, FinanceSnapshot | null>({
    queryKey: queryKeys.business.finances(bizId),
    queryFn: () => businessService.fetchFinanceHistory(),
    select: (list) => {
      if (!list.length) return null;
      return [...list].sort((a, b) => b.snapshot_year - a.snapshot_year)[0];
    },
    enabled: Boolean(bizId),
    staleTime: 60 * 1000,
  });
}
