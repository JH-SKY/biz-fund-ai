# BizMong Agent Observability Plan

## Goal

BizMong, LangGraph routing, and RAG quality should be improved with data, not intuition.

The environment we want is:

- an admin can see question-level cost, latency, routing, and failures
- an admin can compare node-level cost and delay
- prompt or graph changes can be measured before and after
- optimization results can be written up with evidence

Example outcome:

> We found router latency spikes and excessive RAG token usage on policy-interpretation questions.  
> After tightening routing and reducing retrieved context, token cost dropped by 30% while answer quality stayed flat.

## Current Problem

The project already has:

- `chat_logs`
- basic token / latency / cost fields
- admin monitoring pages

But it still lacks the structure needed for true agent optimization:

- turn-level observability is incomplete
- node-level observability is mostly missing
- prompt/version comparisons are not recorded
- admin dashboards do not clearly show where cost and latency come from

## What Must Be Observable

### 1. Turn-level metrics

Every BizMong response should be traceable as one run.

Required fields:

- `run_id`
- `room_id`
- `user_id`
- `business_id`
- `user_message_log_id`
- `assistant_message_log_id`
- `route_intent`
- `final_agent`
- `prompt_version`
- `model_name`
- `status`
- `fallback_mode`
- `fallback_reason`
- `started_at`
- `completed_at`
- `total_latency_ms`
- `first_token_latency_ms`
- `tokens_in`
- `tokens_out`
- `total_cost_usd`
- `rag_hit_count`
- `error_code`
- `error_message`
- `question_preview`

### 2. Node-level metrics

Each meaningful step should be logged separately.

Initial nodes to observe:

- `router`
- `general_qa`
- `rag_retrieval`
- `rag_generation`
- `stats`

Required fields:

- `run_id`
- `node_name`
- `sequence`
- `status`
- `started_at`
- `completed_at`
- `latency_ms`
- `model_name`
- `tokens_in`
- `tokens_out`
- `cost_usd`
- `metadata`

### 3. Optimization outcome metrics

Needed to tell whether changes actually helped:

- response success rate
- error rate
- fallback rate
- re-ask rate
- dislike rate
- diagnosis CTA click-through
- policy matching CTA click-through
- average cost per run
- average latency per run

## Dashboard Requirements

The admin dashboard should make the following visible without opening raw DB rows.

### Agent Overview

- total runs
- success rate
- average latency
- p50 / p95 latency
- total token usage
- total cost
- fallback count

### Intent / Route Breakdown

- runs by intent
- average latency by intent
- average cost by intent
- error rate by intent

### Node Breakdown

- node name
- total executions
- average latency
- p95 latency
- total tokens
- total cost
- error count

### Recent Runs Table

Each row should show:

- timestamp
- session
- user question preview
- route intent
- final agent
- latency
- tokens
- cost
- fallback
- status

### Comparison-Friendly Data

We must be able to compare:

- before vs after prompt change
- before vs after routing change
- before vs after RAG retrieval change

For that reason, each run should eventually support:

- `prompt_version`
- `graph_version`
- `rag_strategy_version`

## Implementation Phases

### Phase 1

Create the minimum usable observability spine.

- add turn-level run log table
- add node-level run log table
- log BizMong stream runs
- log router / general_qa / rag / stats metrics
- expose admin APIs for overview, node stats, recent runs
- surface those in admin monitoring UI

### Phase 2

Make optimization comparison practical.

- add prompt / graph / rag version fields
- add filters by date, intent, route, fallback, model
- add run detail drawer with node timeline
- add CTA conversion tracking

### Phase 3

Support write-up grade optimization reporting.

- baseline snapshot export
- comparison widgets
- anomaly callouts
- downloadable summaries for optimization reports

## Phase 1 Delivery Scope

The current implementation pass should include:

1. observability schema and migration
2. runtime logging for BizMong runs
3. node-level timing and cost capture where available
4. admin monitoring API
5. admin monitoring UI improvements

## Rules While Implementing

- no fake metrics
- if usage data is unavailable, store `null` and expose that clearly
- zero-cost nodes like DB stats can still log latency
- stream path must be the primary source of truth because that is the real user path
- general QA, RAG, and stats must all become comparable in one dashboard

## Success Criteria

This work is successful when:

- a single BizMong question can be traced from user input to final answer
- we can see which node was slow
- we can see which node spent tokens
- we can see which route is expensive
- we can compare changes over time in admin
- future agent optimization can be justified with numbers
