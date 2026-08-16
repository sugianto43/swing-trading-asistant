# Architecture Decision Log

Use this file for decisions that affect multiple phases.

## ADR-0001 — Decision Log
Status: Accepted

Record each decision using:

### ADR-NNNN — Title
Date:
Status:
Context:
Decision:
Alternatives:
Consequences:
Affected phases:

## ADR-0002 — Phase 2 Market Data Vendor: yfinance (Personal-Use POC)
Date: 2026-08-15
Status: Accepted (personal-use scope only; not a production licensing decision)
Context: docs/data/DATA-VENDOR-REQUIREMENTS.md and VENDOR-EVALUATION.md establish a vendor-agnostic
`MarketDataProvider` contract and recommend a Stage 1 prototype using a mock provider plus one
developer-friendly candidate. This application is for personal, non-commercial, single-user use.
No licensed IDX data contract has been evaluated or purchased; the VENDOR-EVALUATION.md matrix
remains entirely "TBD".
Decision: Implement `FixtureProvider` (mandatory mock, used for all automated tests — no
internet dependency) and `YfinanceProvider` (adapter over the unofficial `yfinance` package) as
the two Phase 2 provider implementations, both satisfying the same `MarketDataProvider` protocol.
yfinance was chosen over other free options (e.g. scraping IDX directly) because it has broad
existing IDX (`.JK`) coverage and a stable-enough Python interface for a hobby project.
Alternatives: Twelve Data free tier (official API, more restrictive rate limits, IDX coverage
unverified); a licensed local IDX redistributor (Antara/IMQ, IQ Plus Prima, RTI Infokom) — not
pursued, since that requires a paid commercial contract this project does not have; the
`NeaByteLab/IDX-API` GitHub project (https://github.com/NeaByteLab/IDX-API, MIT-licensed
TypeScript/Deno wrapper) — noted 2026-08-16 as a candidate but not evaluated further or
implemented. Inspection of its `src/Client.ts` shows it works by emulating a browser session
(spoofed User-Agent, scraped session cookie from `idx.co.id/id`) against `idx.co.id/primary/...`
endpoints — IDX's own internal AJAX endpoints that back the public website, not a published or
IDX-sanctioned developer API. Same category of risk as yfinance above (unofficial, reverse-
engineered, no ToS sanctioning third-party programmatic use, and additionally fragile since
internal endpoints can change without notice) but with a materially weaker legal footing since
it directly targets IDX's own site rather than a long-established third-party aggregator, and
a language mismatch (Deno/TypeScript vs. this project's Python backend — would need running as
a separate service or reimplementing the same HTTP calls in Python). If revisited, it must go
through the same before-production evaluation this ADR already requires for yfinance, not be
adopted directly.
Consequences:
- Not a licensed/production data source. Unofficial, reverse-engineered access; Yahoo's terms do
  not sanction this kind of programmatic use. Acceptable only because usage is personal,
  non-commercial, and not redistributed. Must be revisited before any commercial/multi-user use.
- yfinance has no IDX instrument-master API → the instrument universe is bootstrapped from a
  static local seed (`app/marketdata/seed/idx_instruments.csv`), not vendor data.
- yfinance has no trading-calendar API → `trading_calendar` is populated incrementally from
  observed trading days in ingested bars, not a pre-known holiday schedule.
- Corporate actions are limited to what `yfinance`'s `.actions` exposes (dividends, splits) — no
  rights issues, ticker changes, or suspension/relisting events.
- The provider abstraction means swapping to a licensed vendor later requires only a new adapter
  class, not domain/schema changes (per the "vendor can change, canonical contract can't" rule in
  VENDOR-EVALUATION.md §12).
Affected phases: 2 (built), 3+ (consume canonical data only, per the same rule), any future
production go-live (must re-run the full vendor evaluation and licensing gate first).

## ADR-0003 — Phase 8 AI Provider: Google Gemini (Free Tier, Personal-Use POC)
Date: 2026-08-15
Status: Accepted (personal-use scope only; not a production licensing decision)
Context: MASTER-PRD §28 lists "AI provider/model" as an explicit open decision. MASTER-TDD §18
specifies "Provider-agnostic LLM layer with typed tools" — the architecture must not hard-couple
domain logic to one vendor. The user asked for a free option given this is a personal, non-
commercial, single-user project (same framing as ADR-0002).
Decision: Implement `LLMProvider` as a protocol (`app/ai/provider.py`) with two implementations:
`FixtureLLMProvider` (deterministic, scripted, no network — used by every automated test) and
`GeminiProvider` (real adapter over Google's `google-genai` SDK, Gemini's free tier). Gemini was
chosen over Groq and local Ollama because it's hosted (no separate local runtime to install/run),
has a genuinely free tier for personal/low-volume use, and has native tool-calling support that
maps cleanly onto this project's typed-tool registry.
Alternatives: Groq (free tier, hosted, OpenAI-compatible tool-calling — a reasonable second
choice, not pursued since Gemini's tool-calling API integrates slightly more directly); Ollama
(fully local, zero cost, but requires the user to separately install and run a local model runtime
— more setup friction for a decision-support tool meant to be simple to run); Anthropic/OpenAI
(no meaningful free tier for this use case, ruled out per the user's explicit "free option" ask).
Consequences:
- `GeminiProvider` requires `GEMINI_API_KEY` (env var, never committed) to be constructed at all;
  its absence is not an error at import time — only `AIAnalystService._default_provider()` raises,
  and only when no explicit provider is supplied. The full test suite never requires this key.
- The `google-genai` SDK import is local to `GeminiProvider.__init__`/`generate` — no other module
  in `app/ai/` depends on it, so `FixtureLLMProvider`-based tests have zero exposure to SDK version
  drift or network availability.
- Not a production licensing/SLA decision — free-tier rate limits and terms are personal-use
  appropriate only. Must be revisited (per the same discipline as ADR-0002) before any
  commercial/multi-user deployment.
- Swapping providers later (e.g. to a paid tier, or a different vendor) requires only a new
  `LLMProvider` implementation — no changes to `tools.py`, `guardrails.py`, or `orchestrator.py`.
Affected phases: 8 (built). Any future production go-live must re-run a real AI-provider
evaluation (cost, rate limits, data-handling/privacy terms) before relying on this in a
multi-user or commercial context.

## ADR-0004 — No Authentication (Personal-Use, Final)
Date: 2026-08-15
Status: Accepted (final for this project's scope; not a decision that applies to any future
multi-user or commercial deployment)
Context: Every API route has been unauthenticated since Phase 1. This was raised again during
Phase 10's planning (deferred, documented as a gap) and surfaced again during Phase 11 planning —
the last phase on the roadmap (MASTER-PRD §23: `1 -> 2 -> ... -> 10 -> 11`, no Phase 12 exists to
defer it into again). The application is single-user, runs locally (default CORS origin
`http://localhost:3000`, default `DATABASE_URL` points at `localhost`), never executes trades
(AI-GUARDRAILS.md: no automated order execution — every write is a human-initiated API call
recording a decision already made outside the system), and is not exposed to the public internet
in its documented deployment (`docker-compose.yml` binds to the host's own ports, not a public
ingress). A code review of the entire `app/` tree found no raw/string-built SQL taking user
input (the only `text()` usages are a static `SELECT 1` health check and static partial-index
`WHERE` clauses in `models.py`), so the primary risk an unauthenticated single-user local API
carries — arbitrary data exposure/mutation by an untrusted third party — has no network path to
begin with under the documented deployment.
Decision: Do not implement authentication. This is now a permanent, explicit architectural
decision for this project's stated scope (personal, non-commercial, single-user, local), not an
open gap to keep re-raising at each phase.
Alternatives: API-key auth (single shared secret via a header) — rejected as security theater for
a single local user with no network exposure, adding friction (every request, every CLI/worker
call, every AI tool invocation would need to carry/manage a secret) without addressing a real
threat in this deployment shape. Full multi-user auth (OAuth/JWT/sessions) — rejected as
building infrastructure for a use case (multiple users, remote access) this project does not
have and was never scoped for.
Consequences:
- If this application is ever exposed beyond `localhost` (a public server, a shared network, a
  hosted deployment for more than one person), this decision must be revisited before that
  happens — authentication becomes a hard blocker at that point, not an optional hardening step.
- CORS stays scoped to `localhost:3000` by default (`app/config.py`); widening it to a public
  origin without also adding authentication would materially change this decision's risk basis
  and must not be done without re-opening this ADR.
- No route, tool, or worker job in this codebase should ever assume a request is trusted because
  it reached the API — the API itself is the trust boundary today, by design, only because its
  deployment has no network exposure. That assumption breaks the moment deployment shape changes.
Affected phases: all (1-11, retroactively formalizes what was already true); binding on any
future phase or deployment change — re-run this evaluation before removing the localhost-only
assumption above.
