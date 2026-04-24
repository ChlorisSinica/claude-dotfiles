# Phase Overlay: Alignment

## Review Mode

- Cycle type: alignment
- Primary goal: determine whether the implementation matches `plan.md`, `tasks.md`, and any `implementation_gap_audit.md`
- Exit gate: unresolved spec drift = 0

## What To Look For

- Spec drift between implementation and stated task/plan
- Obsolete or partially implemented task wording
- Missing branches, handlers, state transitions, or artifacts that the task requires
- Control-flow drift introduced during implementation
- Changes that solve a neighboring problem instead of the requested one
- Silent scope expansion not reflected in plan/task artifacts
- Mismatch between intended contract and implemented contract

## What To De-Emphasize

- Pure style feedback
- Minor refactors unless they create or conceal drift
- Broad cleanup suggestions unrelated to task/plan alignment

## Alignment-Specific Rules

- Compare intended behavior against actual behavior, not just naming similarity.
- Treat stale comments, stale task text, or stale workflow wording as findings when they can mislead later implementation or review.
- If the implementation appears correct only under assumptions not stated in plan/tasks, call that out as alignment risk.
- If a fix requires changing plan/tasks rather than code, say so explicitly.

## Alignment Verdict Interpretation

- APPROVED: implementation behavior and task/plan intent materially align
- CONDITIONAL: core intent aligns, but some non-blocking drift or documentation/task update remains
- REVISE: required behavior is missing, replaced, contradicted, or materially drifted

## Affirmative Alignment Note

When the implementation materially aligns with plan/tasks, surface that
positive signal as a **single sentence placed immediately before the
`VERDICT:` line** — do not create a dedicated finding bullet for praise.
Keep it one sentence, citing which acceptance criterion is satisfied. Example:

```
Implementation satisfies T1 acceptance criteria (--foo registered, prints
"1.0.0", exits 0); no alignment drift detected.

VERDICT: APPROVED
```

Omit this note entirely when findings exist that contradict alignment.
