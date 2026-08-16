#!/usr/bin/env bash
# Seeds real data into the running Docker backend for the golden-journey
# E2E spec (Phase 18). Run this after `docker compose up -d db redis api`
# and before `npx playwright test`. See README.md in this directory.
set -euo pipefail

cd "$(dirname "$0")/../../.."

docker compose exec api python -m app.marketdata.cli ingest --provider fixture --symbols BBCA
docker compose cp apps/web/e2e/seed_data.py api:/app/e2e_seed_data.py
docker compose exec api python /app/e2e_seed_data.py
# The container's bind mount (./apps/api:/app) means the copied file
# lands on the host too — remove it so it never shows up as an
# apps/api change (this is frontend-owned tooling, not backend code).
rm -f apps/api/e2e_seed_data.py
