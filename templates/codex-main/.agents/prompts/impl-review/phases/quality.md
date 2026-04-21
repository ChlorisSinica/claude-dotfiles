# Phase Overlay: Quality

## Review Mode

- Cycle type: quality
- Primary goal: find regressions, cross-file inconsistencies, boundary contract issues, and recovery weaknesses around the implemented change
- Exit gate: unresolved P0/P1 = 0

## What To Look For

- Regressions in adjacent flows
- Cross-file inconsistencies
- Caller/callee contract mismatch
- Worker/UI payload mismatch
- Helper return shape mismatch
- File or sync artifact contract mismatch
- Startup/init/commit boundary issues
- Recovery or retry behavior that can trap the system in a bad state
- Changes that leave the system harder to diagnose or recover when failure occurs

## Quality-Specific Rules

- Review the changed code in the context of its immediate dependencies, not in isolation.
- Favor concrete boundary analysis over vague maintainability commentary.
- Treat recovery and observability as correctness concerns when failures are expected to occur in practice.
- If a change is locally correct but creates a fragile system interaction, raise that as a finding.
- Distinguish local code cleanliness from actual system robustness.

## Quality Verdict Interpretation

- APPROVED: no unresolved high-severity regression or contract risk remains
- CONDITIONAL: only non-blocking quality risks remain
- REVISE: at least one blocker-level regression or contract failure remains
