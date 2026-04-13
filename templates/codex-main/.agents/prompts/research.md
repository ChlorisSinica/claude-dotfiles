# Research Prompt

Use this when you want Codex to build a deep understanding of the repository before planning or implementation.

## Goals

- Read the relevant code directly
- Respect the research scope in `.agents/AGENTS.md`
- Explain module responsibilities and dependencies
- Identify data flow, important state transitions, and risky assumptions
- Separate facts from open questions

## Expected Output

Write findings to `.agents/context/research.md`.

Recommended sections:

- Overview
- File and module responsibilities
- Dependency relationships
- Data flow
- Key invariants and assumptions
- Risks and open questions

## Rules

- Do not infer behavior from filenames alone.
- Read internals, not just signatures.
- Prioritize source files that match the preset's research scope in `.agents/AGENTS.md`.
- Skip directories whose names start with `.` or `_` unless the task explicitly targets them.
- Treat gitignored workflow/cache artifacts as out of scope unless they are directly relevant.
- Treat paths and file patterns listed in the preset's research exclusions as out of scope unless they are directly relevant.
- If unsure, mark as `要確認`.
- Use `{{VERIFY_CMD}}` if a verification step is needed.
