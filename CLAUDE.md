# IDX Swing Trading Assistant — Claude Code Instructions

Read first:
- MASTER-PRD.md
- MASTER-TDD.md
- MASTER-CLAUDE-INSTRUCTIONS.md
- CODING-STANDARDS.md
- QUANT-TRADING-RULES.md
- AI-GUARDRAILS.md
- DECISION-LOG.md

For phase N also read:
- docs/phase-NN/PRD.md
- docs/phase-NN/TDD.md
- prompts/phase-NN/<workflow>.md

Required workflow:
PLAN → APPROVE → IMPLEMENT → TEST → REVIEW → FIX → REGRESSION → SIGN-OFF → NEXT PHASE

Never skip sign-off or automatically start the next phase.

Scope:
- Implement only the requested phase.
- Never implement future-phase functionality.
- Inspect existing code before changes.
- Preserve accepted architecture decisions.

Quantitative integrity:
- Never use future information.
- Never invent market data.
- Preserve timestamps and source lineage.
- Keep calculations deterministic.
- Treat stale/invalid data explicitly.
- Add adversarial leakage tests where relevant.

AI guardrails:
AI must not execute trades, modify risk limits, access arbitrary SQL, invent numerical facts, invent backtest results, or claim guaranteed outcomes.

Quality:
Run formatter, lint, type checking, relevant tests, and regression tests after changes.

Available skills:
- /plan-phase <N>
- /implement-phase <N>
- /test-phase <N>
- /review-phase <N>
- /fix-phase <N>
- /signoff-phase <N>

A phase is complete only when sign-off returns:
PHASE N STATUS: PROCEED
