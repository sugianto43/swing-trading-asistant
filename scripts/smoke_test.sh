#!/usr/bin/env bash
# Production smoke test (Phase 11, MASTER-PRD §25 "release readiness").
#
# Brings up the real db/redis/api containers via docker-compose, waits for
# health, then checks a handful of endpoints spanning the stack (basic
# health, a read endpoint backed by Postgres, and Phase 10's observability
# endpoint backed by Redis) actually respond. Not a substitute for the
# test suite — this only proves the deployed containers wire up and can
# talk to each other, which nothing in `pytest -q` (SQLite/fakeredis)
# actually exercises.
#
# apps/web is deliberately not started here: it has never been built past
# the Phase 1 scaffold (see DECISION-LOG.md ADR-0004 discussion in the
# Phase 11 plan), so starting it would prove nothing. worker/scheduler ARE
# started and checked below — TDD names "worker failures" as an explicit
# Phase 11 focus, and a smoke test that never proves those containers
# actually boot (vs. crash-looping on a bad import, say) would be
# narrower than what "production smoke test" implies.
set -euo pipefail

cd "$(dirname "$0")/.."

API_BASE="http://localhost:8000"
MAX_WAIT_SECONDS=90
CONTAINER_SETTLE_SECONDS=5

cleanup() {
  echo "--- tearing down ---"
  docker compose down
}
trap cleanup EXIT

echo "--- starting db, redis, api, worker, scheduler ---"
docker compose up -d db redis api worker scheduler

echo "--- waiting for api to become healthy (up to ${MAX_WAIT_SECONDS}s) ---"
elapsed=0
until curl -sf "${API_BASE}/api/v1/health" > /dev/null 2>&1; do
  if [ "${elapsed}" -ge "${MAX_WAIT_SECONDS}" ]; then
    echo "FAIL: api did not become healthy within ${MAX_WAIT_SECONDS}s"
    exit 1
  fi
  sleep 3
  elapsed=$((elapsed + 3))
done

check() {
  local description="$1"
  local url="$2"
  local expected_status="$3"

  status=$(curl -s -o /dev/null -w "%{http_code}" "${url}")
  if [ "${status}" != "${expected_status}" ]; then
    echo "FAIL: ${description} -> expected ${expected_status}, got ${status}"
    exit 1
  fi
  echo "OK: ${description} -> ${status}"
}

check "health"              "${API_BASE}/api/v1/health"          200
check "instruments (DB)"    "${API_BASE}/api/v1/instruments"     200
check "ops status (Redis)"  "${API_BASE}/api/v1/ops/status"      200
check "openapi schema"      "${API_BASE}/openapi.json"           200

echo "--- checking worker/scheduler containers are running, not crash-looping ---"
sleep "${CONTAINER_SETTLE_SECONDS}"
for service in worker scheduler; do
  state=$(docker compose ps --format json "${service}" | python3 -c "import json,sys; print(json.load(sys.stdin)['State'])")
  if [ "${state}" != "running" ]; then
    echo "FAIL: ${service} container state is '${state}', expected 'running'"
    docker compose logs "${service}"
    exit 1
  fi
  echo "OK: ${service} -> running"
done

echo "--- smoke test passed ---"
