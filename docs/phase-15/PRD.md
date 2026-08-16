# Phase 15 — Positions, Journal & Performance UI

## Objective
Build manual execution recording, the open-positions list, journal entry forms, and performance dashboards (MASTER-PRD §14), consuming Phase 7's positions/journal/performance endpoints. Every write is a human recording a decision already made outside the system — the UI never places an order.

## Goals
Implement this phase as a production-quality increment while preserving previous phases.

## Non-Goals
Do not implement features belonging primarily to later phases.

## Critical Requirements
- Read MASTER-PRD.md, MASTER-TDD.md, and the phase TDD before implementation.
- Preserve data integrity and deterministic quantitative behavior.
- Add automated tests.
- Do not implement automated trading.

## Acceptance Criteria
1. Requirements are implemented.
2. Tests cover normal, boundary, and failure cases.
3. Existing tests remain green.
4. Documentation is updated.
5. No critical security/data-integrity defect remains.
6. Definition of Done is explicitly verified.

## Definition of Done
The implementation passes the phase-specific TDD, tests, review, regression suite, and sign-off checklist.
