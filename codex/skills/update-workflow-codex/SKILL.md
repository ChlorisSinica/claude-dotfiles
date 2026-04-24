---
name: update-workflow-codex
description: (Deprecated alias) Forwards to $update-workflow. Kept for backward compatibility after the `-codex` suffix was dropped. Behavior is identical to $update-workflow — refreshes codex-main workflow assets while preserving local context.
---

# Update Workflow Codex (Deprecated Alias)

This skill was renamed to `$update-workflow`. The `-codex` suffix was dropped because the `$` prefix already indicates this is a Codex skill.

The current invocation still works for backward compatibility, but please migrate:

- `$update-workflow-codex <preset>` → `$update-workflow <preset>`

## Workflow

Tell the user once: "`$update-workflow-codex` is a deprecated alias; use `$update-workflow` going forward."

Then run the same workflow as `$update-workflow`:

1. Determine the preset, preferring explicit user input and otherwise inferring from the repository.
2. Run:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py -t codex-main <preset> --workflow-only -f
   ```
   Use a Python 3.11+ launcher such as `python`, `python3`, or `py -3`.
3. Report that local workspaces such as `.agents/context/` and `.agents/reviews/` were preserved.

## Rules

- This file exists only as a migration shim. Do not add new features here — update `$update-workflow` instead.
- Once users have migrated, this stub can be removed in a future release.
