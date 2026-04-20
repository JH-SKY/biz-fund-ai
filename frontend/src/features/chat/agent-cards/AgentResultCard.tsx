"use client";

/**
 * AgentResultCard — agent_type 을 보고 적절한 카드 컴포넌트를 렌더링하는 dispatcher.
 */

import type {
  AgentDiagnosisReport,
  AgentRagResult,
  AgentSimulationReport,
  AgentStatsInsight,
  AgentType,
} from "@/types";
import { DiagnosisCard } from "./DiagnosisCard";
import { SimulatorCard } from "./SimulatorCard";
import { RagCard } from "./RagCard";
import { StatsCard } from "./StatsCard";

interface Props {
  agentType: AgentType;
  diagnosisReport?: AgentDiagnosisReport | null;
  simulationReport?: AgentSimulationReport | null;
  statsInsight?: AgentStatsInsight | null;
  ragResults?: AgentRagResult[] | null;
  /** RAG 의 경우 answer 는 content(text bubble) 에서 이미 표시되므로 선택적 */
  ragAnswer?: string;
}

export function AgentResultCard({
  agentType,
  diagnosisReport,
  simulationReport,
  statsInsight,
  ragResults,
  ragAnswer,
}: Props) {
  if (agentType === "diagnosis" && diagnosisReport) {
    return <DiagnosisCard report={diagnosisReport} />;
  }
  if (agentType === "simulator" && simulationReport) {
    return <SimulatorCard report={simulationReport} />;
  }
  if (agentType === "rag" && ragResults) {
    return <RagCard results={ragResults} answer={ragAnswer} />;
  }
  if (agentType === "stats" && statsInsight) {
    return <StatsCard insight={statsInsight} />;
  }
  return null;
}
