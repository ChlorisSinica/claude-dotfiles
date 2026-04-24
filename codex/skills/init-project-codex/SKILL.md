---
name: init-project-codex
description: (Deprecated alias) Forwards to $init-project. Kept for backward compatibility after the `-codex` suffix was dropped. Behavior is identical to $init-project — runs the codex-main scaffold from this dotfiles setup.
---

# Init Project Codex (Deprecated Alias)

This skill was renamed to `$init-project`. The `-codex` suffix was dropped because the `$` prefix already indicates this is a Codex skill.

The current invocation still works for backward compatibility, but please migrate:

- `$init-project-codex <preset>` → `$init-project <preset>`

## Workflow

Tell the user once: "`$init-project-codex` is a deprecated alias; use `$init-project` going forward."

Then run the same workflow as `$init-project`:

1. Determine the preset (prefer explicit user input; infer from repo otherwise):
   - `.py` -> `python`
   - `.ts` or `.tsx` -> `typescript`
   - `.rs` -> `rust`
   - `.ahk` -> ask only if v1 vs v2 is ambiguous
   - `.sln` or `.vcxproj` -> `cpp-msvc`
   - `.unity` or `Assets/` directory -> `unity`
   - `.blend` -> `blender`
2. Run:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py -t codex-main <preset>
   ```
   Use a Python 3.11+ launcher such as `python`, `python3`, or `py -3`.
3. If the user explicitly wants overwrite behavior, rerun with `-f`.

## Rules

- This file exists only as a migration shim. Do not add new features here — update `$init-project` instead.
- Once users have migrated, this stub can be removed in a future release.
