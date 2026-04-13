---
name: codex-review
description: Review a plan or implementation and save findings under `.agents/reviews/`. Use when the user wants structured plan review, implementation review, re-review after fixes, or a saved review artifact that can be referenced in later iterations.
---

# Codex Review

Run a focused review and save the result for later reuse.

## Inputs To Include

- `.agents/AGENTS.md`
- Relevant files from `.agents/context/`
- Changed source files or diffs
- Prior review output from `.agents/reviews/` when re-reviewing

## Review Priorities

- Correctness
- Behavioral regressions
- Data flow breakage
- Missing verification
- Hidden assumptions

## Output

- Save outputs under `.agents/reviews/`
- Prefer `plan-review.md` or `impl-review.md`
- List findings first, ordered by severity
- If there are no material issues, say so explicitly and mention residual risk briefly
