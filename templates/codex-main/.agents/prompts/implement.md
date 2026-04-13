# Implementation Prompt

Use this when executing tasks from `.agents/context/tasks.md`.

## Working Loop

1. Pick the next unfinished task
2. Make the smallest safe change
3. Run the task-specific verification
4. Run the project-wide verification command
5. If verification fails, diagnose and retry before moving on
6. Update task state only after verification passes

## Rules

- Keep edits surgical
- Avoid unrelated cleanup
- Check upstream and downstream impact when changing interfaces or data flow
- If a failure repeats, copy `.agents/templates/failure_report.md` to `.agents/context/failure_report.md` and fill it in

## Verification

Primary command: `{{VERIFY_CMD}}`
