# Phase 18 — Technical Design Document

## Architecture
Browser E2E testing (Playwright or equivalent — decided in `/plan-phase 18`) driving the MASTER-PRD §24 golden journey through the real UI built in Phases 12-17, against a real backend (Docker Compose), mirroring backend Phase 11's discipline of proving stages actually compose rather than trusting each phase's isolated tests.

## Golden Journey (UI-driven)
Market overview -> scanner candidate selection -> instrument detail -> build trade plan -> AI explanation -> record manual execution -> view open position -> add journal entry -> record exit execution -> view performance -> AI review.

## Audit
Accessibility (automated a11y checks, e.g. axe, on every screen built in Phases 12-17), performance budget (Lighthouse or equivalent — bundle size, initial load), no client-side fabrication of any value the backend didn't return (spot-check against the backend's own guardrails).

## Release
No critical failures, all tests green (component + E2E), production build (`npm run build`) verified in Docker (mirrors backend Phase 11's live smoke-test discipline — actually build and serve the container, not just `npm run dev`).
