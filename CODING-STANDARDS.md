# Coding Standards

## General
Prefer small cohesive modules, explicit interfaces, dependency injection where useful, and deterministic domain logic.

## TypeScript
- strict mode
- no unnecessary `any`
- typed API responses
- reusable domain types
- validation at boundaries

## Python
- type annotations
- small services
- domain logic separated from infrastructure
- explicit exceptions
- deterministic functions for quantitative calculations

## Database
- migrations only
- indexes justified by query patterns
- timestamps explicit
- immutable/auditable execution history

## API
- `/api/v1`
- consistent error envelope
- input validation
- pagination for collections
- no secrets in responses

## Testing
- unit tests for domain logic
- integration tests for DB/API boundaries
- adversarial quantitative tests
- regression tests for previously fixed defects

## Git
Use small logical commits. Do not mix unrelated refactors with feature work.
