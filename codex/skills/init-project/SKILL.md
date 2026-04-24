---
name: init-project
description: Scaffold or refresh a Codex-first (codex-main) project in the current repository. Detects existing scaffolds automatically — fresh repos get a new scaffold; existing ones get a workflow update. Use when the user wants to bootstrap `.agents/` skills / context / reviews / runners, or refresh them after a dotfiles pull.
---

# Init Project (Codex-first, smart mode)

Single entry point for both new scaffolding and workflow updates of the codex-main layout. The Python runner decides init vs update from the manifest automatically; this skill is a thin dispatcher.

## Typical Invocations

- `$init-project ahk` — scaffold or refresh with the ahk preset
- `$init-project python-pytorch` — same with the python-pytorch preset
- `$init-project` — bare invocation refreshes an existing scaffold using the preset recorded in the manifest
- `$init-project --fresh` — force re-init, overwriting all files (nuclear option)
- `Use $init-project to refresh this repo's Codex workflow`

## Input Interpretation

- Treat user text after the skill name as the desired preset when it matches a known preset.
- Supported presets: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`, `unity`, `blender`.
- For the update case, the preset may be omitted — the runner will read it from the manifest.
- If AutoHotkey is detected but version is ambiguous, ask only that one clarifying question.

## Workflow

1. Detect the intent:
   - If the user asked to refresh / update an existing scaffold, the bare form (no preset) works when a manifest exists.
   - If the user is starting fresh or specified a preset, continue with preset determination.

2. Determine the preset when needed:
   - Prefer explicit user input.
   - Otherwise infer from the repository:
     - `.py` -> `python`
     - `.ts` or `.tsx` -> `typescript`
     - `.rs` -> `rust`
     - `.ahk` -> ask only if v1 vs v2 is ambiguous
     - `.sln` or `.vcxproj` -> `cpp-msvc`
     - `.unity` or `Assets/` directory -> `unity`
     - `.blend` -> `blender`

3. Run the Python runner:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py -t codex-main <preset>
   ```
   Use a Python 3.11+ launcher such as `python`, `python3`, or `py -3`.
   - For a refresh on an existing codex-main repo, the `-t codex-main` can be omitted since the manifest encodes it:
     ```text
     <python-launcher> ~/.claude/scripts/init-project.py <preset>
     ```
     Or omit the preset too to reuse the manifest preset:
     ```text
     <python-launcher> ~/.claude/scripts/init-project.py
     ```

4. Handle special exit codes:
   - **exit code 3** (preset mismatch): the runner printed a warning comparing manifest preset and user preset. Ask the user to confirm; if they want to change the preset, re-run with `--accept-preset-change` appended.
   - **exit code 1 with "template cannot be inferred"**: legacy manifest, run with explicit `-t codex-main <preset>` once to migrate.
   - **exit code 1 with "cross-template switch"**: the repo is already scaffolded with a different template. To switch, tell the user they must back up context files and run `rm -rf .claude .agents` first.

5. Report the key generated assets:
   - `.agents/skills/`
   - `.agents/context/`
   - `.agents/reviews/`
   - `scripts/run-verify.py`
   - `scripts/run-codex-plan-review.py`
   - `scripts/run-codex-impl-review.py`
   - `scripts/run-codex-impl-cycle.py`

## Output

Tell the user:

- whether the run was a fresh init or a workflow refresh (based on the runner's "Initialized codex-main preset: ..." line)
- which preset was used
- that repo-local workflow skills live under `.agents/skills/`
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
- If `~/.claude/scripts/init-project.py` is missing, tell the user to refresh the installed workflow assets before retrying (`<python-launcher> ~/claude-dotfiles/scripts/setup.py --codex -f`).
- When the runner reports exit code 3, never silently add `--accept-preset-change` — always surface the preset-change confirmation to the user first.
- This skill replaces the older separate `$init-project-codex` (now deleted) and the former `$update-workflow-codex` / `$update-workflow` skills. There is no longer a separate refresh skill.
