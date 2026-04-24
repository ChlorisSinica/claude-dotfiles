---
name: init-project
description: Initialize the current repository for Codex-first work using the codex-main scaffold from this dotfiles setup. Use when the user wants to bootstrap `.agents/` skills, context folders, review storage, and verification helpers for a project, such as "initialize this repo for Codex", "set up codex-main", or "scaffold the project workflow".
---

# Init Project (Codex-first)

Run the codex-main project scaffold in the current repository.

## Typical Invocations

- `$init-project ahk`
- `$init-project python-pytorch`
- `Use $init-project to initialize this repo for TypeScript`
- `Set up codex-main for this repository with the rust preset`

## Input Interpretation

- Treat the user text after the skill name as the desired preset when it matches a known preset.
- Supported presets:
  - `python`
  - `python-pytorch`
  - `typescript`
  - `rust`
  - `ahk`
  - `ahk-v2`
  - `cpp-msvc`
  - `unity`
  - `blender`
- If the preset is missing, infer it from the repository when possible.
- If AutoHotkey is detected but version is ambiguous, ask only that one clarifying question.

## Workflow

1. Determine the preset.
   Prefer explicit user input. If omitted, infer from the repository:
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
4. Report the key generated assets:
   - `.agents/skills/`
   - `.agents/context/`
   - `.agents/reviews/`
   - `scripts/run-verify.py`
   - `scripts/run-codex-plan-review.py`
   - `scripts/run-codex-impl-review.py`
   - `scripts/run-codex-impl-cycle.py`

## Output

Tell the user:

- which preset was used
- which top-level assets were created
- that repo-local workflow skills now live under `.agents/skills/`
- that newly created repo-local skills may require reopening the Codex / Claude session before they become selectable
- the next suggested entry skills:
  - `.agents/skills/codex-research`
  - `.agents/skills/codex-plan`
  - `.agents/skills/codex-plan-review`
  - `.agents/skills/codex-implement`
  - `.agents/skills/codex-impl-review`
  - `.agents/skills/handover-skills` (for long review / recovery cycles)

## Rules

- This skill is a thin bootstrapper. Do not invent files manually when the scaffold script can generate them.
- Prefer the codex-main scaffold over Claude-oriented templates unless the user explicitly asks for `.claude/` workflow files.
- If `~/.claude/scripts/init-project.py` is missing, tell the user to refresh the installed workflow assets before retrying.
- This skill was formerly named `init-project-codex`; the `-codex` suffix was dropped since the `$` prefix already indicates Codex.
