---
name: sonnet-dp-research-bridge
description: Prepare a neutral handoff for manual Claude/Sonnet research on unresolved discussion points. Use when a design question depends on outside information, vendor comparisons, time-sensitive product behavior, or best-practice research that should be done outside the main Codex implementation flow.
---

# Sonnet DP Research Bridge

Prepare a clean research brief for Claude / Sonnet without generating `.claude/` runtime files.

## Workflow

1. Read the unresolved discussion point from `.agents/context/plan.md`.
2. Fill in `.agents/templates/sonnet-dp-research-input.md`.
3. Use `.agents/prompts/sonnet-dp-research.md` as the handoff prompt for Claude / Sonnet.
4. Save the returned research in `.agents/context/sonnet-dp-research.md`.
5. Use that result as supporting evidence when updating the plan.

## Rules

- Keep the brief neutral.
- Pass evaluation axes and constraints, but do not pre-choose the answer.
- For time-sensitive questions, require official dated sources and clear freshness notes.
