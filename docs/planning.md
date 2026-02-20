# JakeOps Planning

## Product Definition

JakeOps is an orchestration layer that integrates Agent-driven work into existing DevOps pipelines.

- It does not replace CI/CD tools.
- It does not replace coding Agents.
- It tracks state transitions, approvals, and execution evidence.

## Problem Statement

When teams introduce Agents into delivery workflows:

- execution is fragmented,
- context is lost,
- approvals are inconsistent,
- logs/evidence are scattered across systems.

JakeOps addresses this by making each change traceable as one workflow unit (`Delivery`).

## Solution Outline

JakeOps provides:

- Delivery-based orchestration
- Plan -> Approval -> Execution lifecycle
- integration points for CI/CD/observability systems
- evidence retention for audit/debug/review

## Core Workflow

Delivery detected/created
-> Plan generated  
-> Human approval  
-> Implementation  
-> Verification and deployment via external systems  
-> Evidence retained in JakeOps

## Product Positioning

JakeOps is:

- not a CI/CD replacement,
- not a coding assistant,
- not a new pipeline engine.

JakeOps is a control plane for Agent-driven DevOps.

## Competitive Landscape

### Keptn (CNCF Incubating)

Kubernetes-native delivery lifecycle orchestration. Uses SLO-based quality gates
to auto-evaluate deployments via metrics (error rate, latency, etc.).

- Pre/post-deploy tasks, metric evaluation, auto-promotion/rollback
- Tightly coupled to Kubernetes operators
- No AI agent concept — all executors are system-level (K8s operators)
- Focus: "Did this deployment meet SLO targets?"

### Harness

Commercial all-in-one CI/CD platform. Since 2025, adds built-in AI agents:

- Autonomous Code Maintenance (branch, code, test from natural language)
- AI Verification & Rollback (auto-connect observability, detect anomalies)
- Architect Mode (generate pipelines from natural language)
- Closed ecosystem — agents live inside Harness, not pluggable

### How JakeOps Differs

| Dimension | Keptn | Harness | JakeOps |
|-----------|-------|---------|---------|
| Core model | SLO-based deployment gates | All-in-one CI/CD platform | Delivery lifecycle orchestration |
| AI Agent support | None | Built-in, closed | External, pluggable (Claude Code, Devin, etc.) |
| Actor tracking | System only | System + internal AI | System / Agent / Human (explicit) |
| CI/CD relationship | Extends K8s deployments | Replaces CI/CD | Sits above existing CI/CD |
| Evidence & audit | Metric evaluations | Pipeline logs | Agent transcripts, plans, approvals |
| Infrastructure coupling | Kubernetes-native | Harness cloud / self-hosted | Infrastructure-agnostic |
| Cost | Free (OSS) | Enterprise pricing | Free (OSS) |

### JakeOps' Unique Value

The gap that neither Keptn nor Harness fills:

1. **Open agent integration** — any external AI agent (Claude Code, Devin, SWE-agent,
   Copilot Workspace) can be plugged in as an executor. Not locked to one vendor.
2. **Explicit actor model** — every phase transition records whether system, agent,
   or human performed it, enabling audit trails for AI-assisted delivery.
3. **Agent reasoning transcripts** — not just logs, but the agent's full reasoning
   chain: which files it read, which tools it called, what alternatives it
   considered, and why it chose a specific approach. Stored per run as
   `run-{id}.transcript.json` and tied to the Delivery lifecycle. Traditional
   tools record _what_ happened; JakeOps records _why_.
4. **Lightweight overlay** — no infrastructure replacement needed. Works with
   whatever CI/CD, Git hosting, and observability the team already uses.

### Risk: Differentiation Depends on Agent Depth

If JakeOps only tracks phases without deep agent integration, it becomes a
lightweight Keptn clone. The project's defensibility comes from:

- Rich agent↔human handoff UX (plan review, approval, rejection loops)
- Agent transcript/evidence as first-class data
- Multi-agent coordination within a single Delivery
- Provider adapters for popular AI coding agents
