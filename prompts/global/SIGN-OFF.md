# Global Sign-Off Prompt

Verify every requirement in the current phase PRD and TDD.

For each requirement return PASS, FAIL, PARTIAL, or N/A with evidence.

A phase cannot be COMPLETE if any critical requirement is FAIL or PARTIAL.

Run the complete relevant test suite.

Return:
- requirement matrix
- test results
- known issues
- technical debt
- security/data-integrity findings
- final status: PROCEED / DO NOT PROCEED
