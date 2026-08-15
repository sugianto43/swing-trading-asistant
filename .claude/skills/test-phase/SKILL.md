# /test-phase <N>

Read Phase N PRD/TDD and prompts/phase-NN/test.md.

Test:
- happy paths
- boundary cases
- invalid inputs
- missing/stale data
- persistence/API boundaries
- regressions

For quantitative phases additionally test:
- future-data leakage
- timestamp availability
- deterministic reproducibility

Add missing tests but do not add product features. Run relevant and regression suites.
