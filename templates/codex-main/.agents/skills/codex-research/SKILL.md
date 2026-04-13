---
name: codex-research
description: Analyze a repository deeply before planning or implementation and record findings in `.agents/context/research.md`. Use when starting work in an unfamiliar codebase, when preparing a design plan, or when investigating likely bug locations and data flow.
---

# Codex Research

Build a concrete understanding of the repository before making implementation decisions.

## Workflow

1. Read `.agents/AGENTS.md` first and use its research scope to choose files.
2. Read the actual files that matter for the task.
   Skip directories whose names start with `.` or `_` unless the task explicitly targets workflow/config/cache internals there.
3. Identify module responsibilities, dependencies, data flow, and key invariants.
4. Separate observed facts from open questions.
5. Write the results to `.agents/context/research.md`.

## Expected Sections

- Overview
- File and module responsibilities
- Dependency relationships
- Data flow
- Important assumptions and invariants
- Risks and open questions

## Rules

- Read internals, not just file names and signatures.
- Prioritize source files that match the preset's `FILE_PATTERNS`.
- Treat `.`-prefixed and `_`-prefixed directories as out of scope by default.
- Do not spend time on paths or file patterns listed in the preset's research exclusions unless they are directly relevant to the task.
- Do not spend time on gitignored workflow/cache artifacts unless they are directly relevant to the task.
- Do not fabricate bugs or behavior.
- Mark uncertainty as `要確認`.
- Use the verification command from `.agents/AGENTS.md` only when verification materially helps understanding.
