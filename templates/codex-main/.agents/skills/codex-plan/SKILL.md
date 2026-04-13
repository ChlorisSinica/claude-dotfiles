---
name: codex-plan
description: Turn a feature request or bug fix into a concrete implementation plan and task list in `.agents/context/plan.md` and `.agents/context/tasks.md`. Use when the user wants design before coding, when scope needs to be clarified, or when changes affect multiple files or data flow paths.
---

# Codex Plan

Convert a request into a reviewable plan before implementation starts.

## Workflow

1. Read `.agents/context/research.md` when it exists.
2. Define the objective and success criteria.
3. List non-objectives and risks.
4. Identify affected files, interfaces, and data flow.
5. Write a task list with verifiable DoD entries.
6. Save outputs to:
   - `.agents/context/plan.md`
   - `.agents/context/tasks.md`
   - `.agents/context/snippets.md` when pseudocode helps

## Plan Must Cover

- Objective and success criteria
- Non-objectives
- Technical approach and alternatives
- Affected files
- Data flow impact
- Risk and rollback notes
- Verification strategy
- Discussion points for unresolved design decisions

## Rules

- Do not implement while planning.
- Prefer concrete file paths and verifiable tasks.
- If a design question depends on external facts, keep it in Discussion Points and hand it to the Sonnet bridge only when needed.
