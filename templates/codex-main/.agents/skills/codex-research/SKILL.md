---
name: codex-research
description: Analyze a repository deeply before planning or implementation and record findings in `.agents/context/research.md`. Use when starting work in an unfamiliar codebase, when preparing a design plan, or when investigating likely bug locations and data flow.
---

# Codex Research

Build a concrete understanding of the repository before making implementation decisions.

## Workflow

1. Read the actual files that matter for the task.
2. Identify module responsibilities, dependencies, data flow, and key invariants.
3. Separate observed facts from open questions.
4. Write the results to `.agents/context/research.md`.

## Expected Sections

- Overview
- File and module responsibilities
- Dependency relationships
- Data flow
- Important assumptions and invariants
- Risks and open questions

## Rules

- Read internals, not just file names and signatures.
- Do not fabricate bugs or behavior.
- Mark uncertainty as `要確認`.
- Use the verification command from `.agents/AGENTS.md` only when verification materially helps understanding.
