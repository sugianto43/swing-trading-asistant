# Phase 10 — Technical Design Document

## Architecture
FastAPI + PostgreSQL + Redis + workers + scheduler + Next.js/SSE.

## Jobs
Ingestion → validation → indicators → scanner → risk → opportunities → alerts.

## Reliability
Retries, dead-letter handling, distributed locks, provider fallback, stale-data pause.

## Monitoring
Logs, queue depth, worker health, latency, freshness, error rates.

## Tests
Provider outage, Redis outage, DB outage, worker crash, duplicate job, stale data, duplicate alert.
