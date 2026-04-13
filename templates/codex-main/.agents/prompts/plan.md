# Planning Prompt

Use this when turning a feature request or bug fix into an implementation plan.

## Preconditions

- `.agents/context/research.md` should exist for non-trivial work

## Expected Output

Write to:

- `.agents/context/plan.md`
- `.agents/context/tasks.md`
- `.agents/context/snippets.md` when pseudocode helps

## Plan Must Include

1. Objective and success criteria
2. Non-objectives
3. Technical approach and alternatives
4. Affected files
5. Data flow impact
6. Risk and rollback notes
7. Verification plan
8. Discussion points for unresolved decisions

## Task Rules

- Tasks should be independently verifiable
- Each task should have a clear DoD
- Do not implement during planning
