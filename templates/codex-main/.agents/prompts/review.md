# Review Prompt

Use this for Codex plan review or implementation review.

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

Save review results under `.agents/reviews/`.
Recommended files:

- `plan-review.md`
- `impl-review.md`

List findings first, ordered by severity.
