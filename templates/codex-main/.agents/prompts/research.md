# Research Prompt

Use this when you want Codex to build a deep understanding of the repository before planning or implementation.

## Goals

- Read the relevant code directly
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
- If unsure, mark as `要確認`.
- Use `{{VERIFY_CMD}}` if a verification step is needed.
