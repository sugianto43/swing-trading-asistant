# /implement-phase <N>

Read all master docs plus Phase N PRD/TDD and prompts/phase-NN/implement.md.

Confirm an approved plan exists. If not, ask the user to run /plan-phase N.

Implement Phase N only. Never implement future phases.

Add/update tests. Run:
- formatter
- lint
- type checking
- relevant tests
- regression tests

Fix failures caused by the implementation.

Report files changed, decisions, tests, failures, limitations, and PRD coverage.
