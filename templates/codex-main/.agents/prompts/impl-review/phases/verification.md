# Phase Overlay: Verification

## Review Mode

- Cycle type: verification
- Primary goal: determine whether the implementation has enough evidence to believe the task works as intended
- Exit gate: required verification passed or any remaining gap is explicitly documented and accepted

## Verification Lens

Always distinguish these layers:

- static verification: compile, lint, type, schema, obvious local reasoning
- direct runtime probe: focused execution, targeted repro, narrow manual check
- real-environment validation: actual host/application/integration behavior

## What To Look For

- Claims of correctness that are unsupported by evidence
- Code paths that appear correct statically but are high-risk at runtime
- Missing or weak verification for changed boundaries
- Regressions likely to appear only in integration, startup, worker, UI, file, or synchronization paths
- Error handling paths that were not realistically exercised
- Fixes that patch symptoms without validating the underlying behavior

## Verification-Specific Rules

- Do not assume runtime correctness from static plausibility alone.
- If verification was attempted through a wrapper and the wrapper itself failed, separate wrapper failure from code failure.
- Treat untested high-risk paths as findings when the task depends on them.
- Call out whether evidence is static-only, runtime-probed, or real-environment validated.
- Prefer concrete verification gaps over generic “needs more testing” statements.
- Fresh scaffold behavior and the declared dogfood scope are the default verification priority.
- If the fresh path works and the remaining concern is only broader cleanup completeness outside the current slice, record it as a residual risk or follow-up task instead of blocking verification.

## Verification Verdict Interpretation

- APPROVED: required behavior has adequate evidence for this task slice
- CONDITIONAL: implementation looks plausible, but some important verification evidence is still missing
- REVISE: verification evidence indicates failure, or the absence of evidence is too severe to trust the implementation
