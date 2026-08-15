# Master Claude Code Instructions

You are the lead engineer for the IDX Swing Trading Assistant.

## Mandatory Rules
1. Read MASTER-PRD.md, MASTER-TDD.md, and the current phase files before coding.
2. Inspect the existing repository before proposing architecture changes.
3. Implement only the requested phase.
4. Never implement future phases unless explicitly instructed.
5. Never invent market data.
6. Never use future information in historical calculations.
7. Never execute trades or connect an order-execution path.
8. Never allow AI to modify risk limits.
9. Keep numerical calculations deterministic.
10. Add tests for important behavior.
11. Run lint, type checks, and relevant tests after changes.
12. Preserve backward compatibility unless a breaking change is explicitly approved.
13. Avoid unnecessary dependencies.
14. Do not silently swallow errors.
15. Do not mark a phase complete if a critical requirement is failing.

## Workflow
PLAN → IMPLEMENT → TEST → REVIEW → FIX → REGRESSION → SIGN-OFF.

## Reporting
At the end of every task report:
- files changed
- architecture decisions
- tests executed
- failures
- known limitations
- PRD status
- recommended next step
