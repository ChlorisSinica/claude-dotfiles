---
name: update-workflow-codex
description: Refresh an existing repository's codex-main workflow assets while preserving local context and review artifacts. Use when the user wants to update `.agents/skills`, prompts, templates, or verification helpers in a Codex-first project without wiping ongoing work.
---

# Update Workflow Codex

Refresh repo-local Codex workflow assets for a project already using the codex-main scaffold.

## Typical Invocations

- `$update-workflow-codex ahk`
- `$update-workflow-codex python`
- `Use $update-workflow-codex to refresh this repo's Codex workflow`
- `Refresh the codex-main workflow for this repository with the rust preset`

## Input Interpretation

- Treat the user text after the skill name as the desired preset when it matches a known preset.
- If the preset is omitted, infer it from the repository when possible.
- Preserve local context and review artifacts by default.

## Workflow

1. Determine the preset, preferring explicit user input and otherwise inferring from the repository.
2. Run:
   ```bash
   bash ~/.claude/scripts/init-project.sh --codex-main <preset> --workflow-only -f
   ```
3. Report that local workspaces such as `.agents/context/` and `.agents/reviews/` were preserved.

## Output

Tell the user:

- which preset was used
- which workflow assets were refreshed
- that `.agents/context/` and `.agents/reviews/` were preserved
- whether `scripts/run-verify.sh` or `scripts/run-verify.ps1` were updated

## Rules

- Do not remove `.agents/context/` or `.agents/reviews/` during workflow refresh.
- Prefer workflow refresh over a full overwrite when the user is already mid-project.
- If the bootstrap script is missing, direct the user to `bash ~/claude-dotfiles/setup.sh -f --codex`.
