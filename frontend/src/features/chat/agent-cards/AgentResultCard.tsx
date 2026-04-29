"use client";

import type { AgentRagResult, AgentStatsInsight, AgentType } from "@/types";
import { RagCard } from "./RagCard";
import { StatsCard } from "./StatsCard";

interface Props {
  agentType: AgentType;
  statsInsight?: AgentStatsInsight | null;
  ragResults?: AgentRagResult[] | null;
  ragAnswer?: string;
}

export function AgentResultCard({
  agentType,
  statsInsight,
  ragResults,
  ragAnswer,
}: Props) {
  if (agentType === "rag" && ragResults) {
    return <RagCard results={ragResults} answer={ragAnswer} />;
  }
  if (agentType === "stats" && statsInsight) {
    return <StatsCard insight={statsInsight} />;
  }
  return null;
}
