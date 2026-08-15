# /signoff-phase <N>

Read master docs, Phase N PRD/TDD, and prompts/phase-NN/sign-off.md.

Verify every requirement as:
PASS / FAIL / PARTIAL / N/A

Provide evidence.

Verify:
- tests
- lint
- type checking
- build where applicable
- security
- data integrity
- phase scope

Do not modify code.

Return exactly one:
PHASE N STATUS: PROCEED
or
PHASE N STATUS: DO NOT PROCEED

Never automatically start the next phase.
