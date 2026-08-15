# IDX Swing Trading Assistant — Claude Code Package

## Contents
- MASTER-PRD.md
- MASTER-TDD.md
- MASTER-CLAUDE-INSTRUCTIONS.md
- CODING-STANDARDS.md
- QUANT-TRADING-RULES.md
- AI-GUARDRAILS.md
- DECISION-LOG.md
- docs/phase-01..11/PRD.md
- docs/phase-01..11/TDD.md
- prompts/global/*
- prompts/phase-01..11/*

## Recommended Claude Code Workflow

For each phase:

1. Read the master files.
2. Run `prompts/phase-XX/plan.md`.
3. Review/approve the plan.
4. Run `prompts/phase-XX/implement.md`.
5. Run `prompts/phase-XX/test.md`.
6. Run `prompts/phase-XX/review.md`.
7. Approve fixes.
8. Run `prompts/phase-XX/fix.md`.
9. Run `prompts/phase-XX/sign-off.md`.
10. Only proceed when status is PROCEED.

## Example

```text
Read docs/MASTER-PRD.md
Read docs/phase-03/PRD.md
Read docs/phase-03/TDD.md
Read prompts/phase-03/plan.md

Execute the planning workflow only.
Do not modify code.
```

Then, after approval:

```text
Read prompts/phase-03/implement.md
Execute the Phase 3 implementation workflow.
```

## Important
These files define engineering requirements. Actual IDX data-provider selection must separately verify licensing, API terms, historical depth, latency, and redistribution rights.

## Local Development (Phase 1 — Foundation)

### Prerequisites
- Docker + Docker Compose
- Python 3.12+ (for running API tooling outside Docker)
- Node 22+ (for running web tooling outside Docker)

### Run everything with Docker Compose
```bash
cp .env.example .env
docker compose up --build
```
- API: http://localhost:8000/api/v1/health
- Web: http://localhost:3000

### API (apps/api) — local, without Docker
```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# quality gates
ruff format . && ruff check . && mypy app && pytest -q
```

### Web (apps/web) — local, without Docker
```bash
cd apps/web
npm ci
npm run dev

# quality gates (build before tsc: Next.js generates route types during build)
npm run lint && npm run build && npx tsc --noEmit && npm test
```

### CI
`.github/workflows/ci.yml` runs API lint/type-check/tests, an Alembic migration up/down check against a real Postgres service container, and web lint/type-check/test/build on every push and pull request.
