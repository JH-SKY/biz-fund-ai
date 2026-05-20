/**
 * 진단(diagnoses) / 시뮬레이션(simulations) 도메인 API.
 *
 * 백엔드 매핑 (backend/src/app/api/v1/diagnosis_router.py)
 *  - GET  /diagnoses                  → fetchHistory   ← [대시보드 '마지막 진단']
 *  - GET  /diagnoses/{id}             → fetchDetail
 *  - POST /diagnoses                  → execute
 *  - GET  /diagnoses/prepare          → prepare
 */

import apiClient from "@/lib/api-client";
import type {
  DiagnosisDetail,
  DiagnosisHistoryItem,
  ExecuteDiagnosisRequest,
  ExecuteDiagnosisResponse,
  ExecuteSimulationRequest,
  ExecuteSimulationResponse,
  PrepareDiagnosisResponse,
} from "@/types";

export const diagnosisService = {
  prepare: () =>
    apiClient.get<PrepareDiagnosisResponse>("/diagnoses/prepare"),

  execute: (body: ExecuteDiagnosisRequest) =>
    apiClient.post<ExecuteDiagnosisResponse>("/diagnoses", body),

  fetchHistory: (limit?: number) =>
    apiClient.get<DiagnosisHistoryItem[]>("/diagnoses", { params: { limit } }),

  fetchDetail: (diagnosisId: string) =>
    apiClient.get<DiagnosisDetail>(`/diagnoses/${diagnosisId}`),

  executeSimulation: (body: ExecuteSimulationRequest) =>
    apiClient.post<ExecuteSimulationResponse>("/simulations", body),
};
