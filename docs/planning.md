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

JakeOps addresses this by making each change traceable as one workflow unit (`Issue`).

## Solution Outline

JakeOps provides:

- Issue-based orchestration
- Plan -> Approval -> Execution lifecycle
- integration points for CI/CD/observability systems
- evidence retention for audit/debug/review

## Core Workflow

Issue detected/created  
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
