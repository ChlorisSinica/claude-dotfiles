---
name: codex-implement
description: Execute the next planned task from `.agents/context/tasks.md` with surgical edits and verification after each meaningful change. Use when planning is complete and the user wants implementation to proceed in small, verifiable steps.
---

# Codex Implement

Implement planned work incrementally while keeping verification tight.

## Workflow

1. Read `.agents/context/tasks.md`.
2. Pick the next unfinished task.
3. Make the smallest safe change that satisfies that task.
4. Run task-specific verification if present.
5. Run the project-wide verification command from `.agents/AGENTS.md`.
6. Only mark the task complete after verification passes.

## Rules

- Keep edits surgical.
- Avoid unrelated refactors.
- When interfaces or data flow change, verify upstream and downstream impact.
- If the same failure repeats, copy `.agents/templates/failure_report.md` to `.agents/context/failure_report.md` and fill it in.
