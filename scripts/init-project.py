#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


RUNNER_FILES = (
    "fix_codex_plugin_prompts.py",
    "run-codex-plan-review.py",
    "run-codex-impl-review.py",
    "run-codex-impl-cycle.py",
    "run-verify.py",
)
SHELL_CONTROL_TOKENS = ("&&", "||", "|", ";", ">", "<", "$(")
MIN_PYTHON = (3, 11)
RETIRED_CODEX_RUNNERS = (
    "run-codex-plan-review.ps1",
    "run-codex-impl-review.ps1",
    "run-verify.sh",
    "run-verify.ps1",
)
RETIRED_STANDARD_RUNNERS = (
    "run-verify.sh",
    "run-verify.ps1",
)
CODEX_ONLY_RUNNERS = tuple(name for name in RUNNER_FILES if name != "run-verify.py")
WORKFLOW_MANIFEST_NAME = ".claude-dotfiles-managed.json"


@dataclass
class WorkflowManifestData:
    managed: set[str]
    preset: str | None = None
    template: str | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize the current repository with the codex-main Python-first scaffold.")
    parser.add_argument(
        "-t",
        "--template",
        default=None,
        help="Template name: project-init (default), codex-main, research-survey",
    )
    parser.add_argument("preset", nargs="?")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--update",
        action="store_true",
        help="Force update mode. Refreshes managed files while preserving context/ and user-added files.",
    )
    mode_group.add_argument(
        "--fresh",
        action="store_true",
        help="Force fresh init. Overwrites all files (managed and unmanaged) with the new scaffold.",
    )
    parser.add_argument(
        "--accept-preset-change",
        action="store_true",
        help="Non-interactively accept changing the preset recorded in the manifest.",
    )
    return parser.parse_args(argv)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def script_root() -> Path:
    return Path(__file__).resolve().parent


def repo_root_from_script() -> Path:
    return script_root().parent


def discover_template_root(template_name: str) -> Path:
    local_template = repo_root_from_script() / "templates" / template_name
    if local_template.is_dir():
        return local_template
    home = Path.home()
    installed_template = home / ".claude" / "templates" / template_name
    if installed_template.is_dir():
        return installed_template
    raise FileNotFoundError(f"{template_name} template not found at {local_template} or {installed_template}")


def discover_script_source_dir() -> Path:
    local_scripts = repo_root_from_script() / "scripts"
    if local_scripts.is_dir():
        return local_scripts
    installed_scripts = Path.home() / ".claude" / "scripts"
    if installed_scripts.is_dir():
        return installed_scripts
    raise FileNotFoundError("scripts directory not found for runner copy.")


def load_presets(template_root: Path) -> dict[str, Any]:
    presets_path = template_root / "presets.json"
    data = json.loads(read_text(presets_path))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid presets file: {presets_path}")
    return data


def substitute_content(content: str, preset: dict[str, Any]) -> str:
    result = content
    for key, value in preset.items():
        result = result.replace(f"{{{{{key}}}}}", "" if value is None else str(value))
    return result


def should_skip_template_file(relative_path: str, *, workflow_only: bool, skills_only: bool, workflow_root: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    if workflow_root == ".agents" and normalized == "prompts/codex_impl_review.md":
        # Fresh codex-main scaffolds rebuild the legacy prompt from the split prompt parts.
        return True
    if skills_only:
        return workflow_root == ".agents" and not normalized.startswith("skills/")
    if workflow_only:
        if workflow_root == ".agents":
            return normalized.startswith("context/") or normalized.startswith("reviews/")
        return normalized.startswith("context/") or normalized == "agents/sessions.json"
    return False


class InitCollisionError(RuntimeError):
    """Raised when init mode detects files at template paths without a manifest."""

    def __init__(self, collisions: list[str]):
        self.collisions = collisions
        preview = "\n".join(f"  - {p}" for p in collisions[:10])
        suffix = "" if len(collisions) <= 10 else f"\n  ... and {len(collisions) - 10} more"
        super().__init__(
            "init mode cannot proceed: existing files at template paths without a scaffold manifest.\n"
            f"{preview}{suffix}\n"
            "Resolve by either:\n"
            "  (a) removing the colliding files and re-running, or\n"
            "  (b) re-running with --fresh to overwrite them."
        )


def copy_template_tree(
    template_workflow_dir: Path,
    dest_workflow_dir: Path,
    preset: dict[str, Any],
    *,
    force: bool,
    workflow_only: bool,
    skills_only: bool,
    workflow_root: str,
    previously_managed: set[str] | None = None,
    overwrite_unmanaged: bool = False,
) -> set[str]:
    """Copy template files to destination, respecting the active mode.

    - `force=False` (init mode): raise InitCollisionError if any template path is
      already occupied by an unmanaged file.
    - `force=True, overwrite_unmanaged=False` (update mode): overwrite files tracked
      in `previously_managed`, keep user-owned collisions at template paths.
    - `force=True, overwrite_unmanaged=True` (fresh mode): overwrite everything at
      template paths regardless of manifest tracking (nuclear re-init).
    """
    previously_managed = previously_managed or set()
    expected: set[str] = set()

    if not force:
        collisions: list[str] = []
        for src in template_workflow_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(template_workflow_dir).as_posix()
            if should_skip_template_file(rel, workflow_only=workflow_only, skills_only=skills_only, workflow_root=workflow_root):
                continue
            dst = dest_workflow_dir / rel
            if dst.exists() and rel not in previously_managed:
                collisions.append(f"{workflow_root}/{rel}")
        if collisions:
            raise InitCollisionError(sorted(collisions))

    for src in template_workflow_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(template_workflow_dir).as_posix()
        if should_skip_template_file(rel, workflow_only=workflow_only, skills_only=skills_only, workflow_root=workflow_root):
            continue
        dst = dest_workflow_dir / rel
        if dst.exists():
            if not force:
                if rel in previously_managed:
                    expected.add(rel)
                continue
            if rel not in previously_managed and not overwrite_unmanaged:
                continue
        try:
            content = substitute_content(read_text(src), preset)
            write_text(dst, content)
        except UnicodeDecodeError:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        expected.add(rel)
    return expected


def read_workflow_manifest_data(path: Path) -> WorkflowManifestData:
    if not path.is_file():
        return WorkflowManifestData(managed=set())
    try:
        data = json.loads(read_text(path))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Unable to read workflow manifest: {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Workflow manifest has invalid structure: {path}")
    entries = data.get("managed", [])
    if not isinstance(entries, list):
        raise RuntimeError(f"Workflow manifest has invalid structure: {path}")
    preset = data.get("preset")
    template = data.get("template")
    return WorkflowManifestData(
        managed={str(item) for item in entries if isinstance(item, str) and item},
        preset=preset if isinstance(preset, str) and preset else None,
        template=template if isinstance(template, str) and template else None,
    )


def detect_active_template(repo_root: Path) -> tuple[str | None, str | None, bool]:
    """Return (active_template, manifest_preset, legacy_uninferable).

    - `(None, None, False)`: no manifest at all → init mode
    - `(<template>, <preset>, False)`: tagged manifest (new schema) → preset may be None
    - `(<inferred_template>, None, False)`: legacy manifest, template inferred from managed paths
    - `(None, None, True)`: legacy manifest present but template could not be inferred

    Parse errors are tolerated per-file: a readable manifest is used even if the
    other one is corrupt.  Only when **all present manifests fail to parse** does
    the function raise — the caller is responsible for routing that error (e.g.
    --fresh should fall back to None/None rather than abort).
    """
    agents_manifest = repo_root / ".agents" / WORKFLOW_MANIFEST_NAME
    claude_manifest = repo_root / ".claude" / WORKFLOW_MANIFEST_NAME

    agents_data: WorkflowManifestData | None = None
    claude_data: WorkflowManifestData | None = None
    agents_parse_error: Exception | None = None
    claude_parse_error: Exception | None = None

    if claude_manifest.is_file():
        try:
            claude_data = read_workflow_manifest_data(claude_manifest)
        except RuntimeError as exc:
            claude_parse_error = exc
    if agents_manifest.is_file():
        try:
            agents_data = read_workflow_manifest_data(agents_manifest)
        except RuntimeError as exc:
            agents_parse_error = exc

    # If all present manifests failed, surface the error so non-fresh callers can
    # exit with guidance to use --fresh.
    if agents_data is None and claude_data is None:
        if agents_parse_error is not None and claude_parse_error is not None:
            raise claude_parse_error
        if claude_parse_error is not None:
            raise claude_parse_error
        if agents_parse_error is not None:
            raise agents_parse_error
        return None, None, False

    # Authoritative: .claude/manifest.template when present (codex-main writes it too).
    if claude_data is not None and claude_data.template:
        return claude_data.template, claude_data.preset, False

    # Legacy inference from managed paths — .agents first (unique codex-main marker).
    if agents_data is not None and any(m.startswith("skills/") for m in agents_data.managed):
        return "codex-main", agents_data.preset, False

    # Legacy inference from .claude managed paths even if .agents is corrupt.
    if claude_data is not None:
        managed = claude_data.managed
        if "commands/search.md" in managed or "commands/check-tools.md" in managed:
            return "research-survey", claude_data.preset, False
        if "commands/plan.md" in managed or "commands/implement.md" in managed:
            return "project-init", claude_data.preset, False

    # Manifest present but template cannot be inferred.
    return None, None, True


def read_workflow_manifest(path: Path) -> set[str]:
    return read_workflow_manifest_data(path).managed


def read_workflow_manifest_tolerant(path: Path) -> set[str]:
    """Like read_workflow_manifest but returns an empty set if the manifest is
    missing or corrupt. Intended for the --fresh recovery path where the caller
    explicitly wants to reinitialize from scratch."""
    try:
        return read_workflow_manifest(path)
    except RuntimeError:
        return set()


def write_workflow_manifest(
    path: Path,
    entries: set[str],
    *,
    preset: str | None = None,
    template: str | None = None,
) -> None:
    data: dict[str, Any] = {"managed": sorted(entries)}
    if preset is not None:
        data["preset"] = preset
    if template is not None:
        data["template"] = template
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def should_preserve_workflow_file(relative_path: str, *, workflow_only: bool, skills_only: bool, workflow_root: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    if normalized == ".claude-dotfiles-managed.json":
        return True
    if skills_only and not normalized.startswith("skills/"):
        return True
    if workflow_root == ".agents":
        return (
            normalized.startswith("context/")
            or normalized.startswith("reviews/")
            or normalized.startswith("logs/")
        )
    return (
        normalized.startswith("context/")
        or normalized.startswith("logs/")
        or normalized == "agents/sessions.json"
    )


def prune_workflow_tree(
    dest_workflow_dir: Path,
    *,
    expected: set[str],
    force: bool,
    workflow_only: bool,
    skills_only: bool,
    workflow_root: str,
    preset_name: str | None = None,
    template_name: str | None = None,
    overwrite_unmanaged: bool = False,
) -> None:
    manifest_path = dest_workflow_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = (
        read_workflow_manifest_tolerant(manifest_path)
        if overwrite_unmanaged
        else read_workflow_manifest(manifest_path)
    )
    if force and dest_workflow_dir.is_dir():
        for path in sorted((item for item in dest_workflow_dir.rglob("*") if item.is_file()), reverse=True):
            relative = path.relative_to(dest_workflow_dir).as_posix()
            if should_preserve_workflow_file(
                relative,
                workflow_only=workflow_only,
                skills_only=skills_only,
                workflow_root=workflow_root,
            ):
                continue
            if relative not in expected and relative in previously_managed:
                path.unlink()
        for directory in sorted((item for item in dest_workflow_dir.rglob("*") if item.is_dir()), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                continue
    manifest_entries = set(expected)
    if not force:
        manifest_entries.update(
            entry for entry in previously_managed if (dest_workflow_dir / entry).exists()
        )
    manifest_entries.update(
        entry
        for entry in previously_managed
        if should_preserve_workflow_file(
            entry,
            workflow_only=workflow_only,
            skills_only=skills_only,
            workflow_root=workflow_root,
        )
        and (dest_workflow_dir / entry).exists()
    )
    if skills_only:
        manifest_entries.update(entry for entry in previously_managed if not entry.startswith("skills/"))
    write_workflow_manifest(
        manifest_path,
        manifest_entries,
        preset=preset_name,
        template=template_name,
    )


def build_legacy_impl_review_prompt(
    dest_agents_dir: Path,
    *,
    force: bool,
    previously_managed: set[str],
    skills_only: bool,
    overwrite_unmanaged: bool = False,
) -> bool:
    if skills_only:
        return "prompts/codex_impl_review.md" in previously_managed
    prompt_root = dest_agents_dir / "prompts" / "impl-review"
    core = prompt_root / "core.md"
    quality = prompt_root / "phases" / "quality.md"
    preset = prompt_root / "preset.md"
    if not (core.is_file() and quality.is_file()):
        return False
    legacy_rel = "prompts/codex_impl_review.md"
    legacy_path = dest_agents_dir / legacy_rel
    if legacy_path.exists():
        if not force:
            if legacy_rel not in previously_managed:
                raise InitCollisionError([f".agents/{legacy_rel}"])
            return True
        if legacy_rel not in previously_managed and not overwrite_unmanaged:
            return False
    parts = [read_text(core).strip(), read_text(quality).strip()]
    if preset.is_file():
        parts.append(read_text(preset).strip())
    write_text(legacy_path, "\n\n".join(part for part in parts if part).rstrip() + "\n")
    return True


def seed_context_files(dest_agents_dir: Path, *, force: bool, workflow_only: bool, skills_only: bool) -> None:
    if skills_only:
        return
    if workflow_only:
        return
    context_dir = dest_agents_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    seed_map = {
        "research.md": "# Research\n\n## Findings\n\n- \n",
        "plan.md": "# Plan\n\n## Goal\n\n- \n",
        "tasks.md": "# Tasks\n\n- [ ] \n",
        "implementation_gap_audit.md": "# Implementation Gap Audit\n\n## Known Gaps\n\n- \n",
    }
    for name, content in seed_map.items():
        path = context_dir / name
        if not path.exists():
            write_text(path, content)


def seed_standard_context(dest_claude_dir: Path, *, force: bool, workflow_only: bool) -> None:
    context_dir = dest_claude_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = context_dir / ".gitkeep"
    if workflow_only and gitkeep.exists():
        return
    if force or not gitkeep.exists():
        write_text(gitkeep, "")


def prune_manifest_owned_paths(root: Path, managed_entries: set[str], *, keep: set[str]) -> None:
    for entry in sorted(managed_entries):
        if entry in keep:
            continue
        path = root / entry
        if path.is_file():
            path.unlink()
    for directory in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def require_existing_codex_runners(repo_root: Path) -> None:
    missing = [name for name in ("run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py") if not (repo_root / "scripts" / name).is_file()]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"--skills-only requires an existing codex-main runner set. Missing: {joined}. Run full --codex-main first."
        )


def copy_runner_files(
    source_scripts_dir: Path,
    dest_repo_root: Path,
    *,
    force: bool,
    overwrite_unmanaged: bool = False,
) -> set[str]:
    dest_scripts_dir = dest_repo_root / "scripts"
    dest_scripts_dir.mkdir(parents=True, exist_ok=True)
    expected: set[str] = set()
    manifest_path = dest_scripts_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = (
        read_workflow_manifest_tolerant(manifest_path)
        if overwrite_unmanaged
        else read_workflow_manifest(manifest_path)
    )
    if not force:
        collisions = [
            f"scripts/{name}"
            for name in RUNNER_FILES
            if (dest_scripts_dir / name).exists() and name not in previously_managed
        ]
        if collisions:
            raise InitCollisionError(sorted(collisions))
    for name in RUNNER_FILES:
        src = source_scripts_dir / name
        if not src.is_file():
            raise FileNotFoundError(f"Required runner not found: {src}")
        dst = dest_scripts_dir / name
        if dst.exists():
            if not force:
                if name in previously_managed:
                    expected.add(name)
                continue
            if name not in previously_managed and not overwrite_unmanaged:
                continue
        shutil.copy2(src, dst)
        expected.add(name)
    return expected


def command_requires_shell(command: str) -> bool:
    return any(token in command for token in SHELL_CONTROL_TOKENS)


def probe_python_launcher(candidate: tuple[str, ...]) -> bool:
    executable = shutil.which(candidate[0])
    if not executable:
        return False
    try:
        result = subprocess.run(
            [*candidate, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    match = re.match(r"^\s*(\d+)\.(\d+)\s*$", result.stdout)
    if not match:
        return False
    version = (int(match.group(1)), int(match.group(2)))
    return version >= MIN_PYTHON


def discover_portable_python_launcher() -> str:
    candidates = [("python3",), ("python",)]
    if os.name == "nt":
        candidates.insert(0, ("py", "-3"))
    for candidate in candidates:
        if probe_python_launcher(candidate):
            return " ".join(candidate)
    raise RuntimeError(
        "Unable to find a portable Python launcher. Expected one of `py`, `python3`, or `python` on PATH."
    )


def default_portable_python_launcher() -> str:
    return "py -3" if os.name == "nt" else "python3"


def infer_existing_python_launcher(repo_root: Path) -> str | None:
    candidates = (
        repo_root / ".agents" / "skills" / "codex-plan-review" / "SKILL.md",
        repo_root / ".agents" / "skills" / "codex-impl-review" / "SKILL.md",
        repo_root / ".agents" / "skills" / "codex-fkin-impl-cycle" / "SKILL.md",
        repo_root / ".agents" / "AGENTS.md",
    )
    patterns = (
        r"`([^`\r\n]+?)\s+scripts/run-codex-plan-review\.py\b",
        r"`([^`\r\n]+?)\s+scripts/run-codex-impl-review\.py\b",
        r"`([^`\r\n]+?)\s+scripts/run-codex-impl-cycle\.py\b",
        r"`([^`\r\n]+?)\s+scripts/run-verify\.py\b",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            content = read_text(path)
        except OSError:
            continue
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                launcher = match.group(1).strip()
                if launcher:
                    return launcher
    return None


def materialize_verify_command(command: str, launcher: str) -> str:
    if not command.strip():
        return command
    patterns = (
        (r"(?<!\S)python3(?=\s)", launcher),
        (r"(?<!\S)python(?=\s)", launcher),
        (r"(?<!\S)py\s+-3(?=\s)", launcher),
    )
    updated = command
    for pattern, replacement in patterns:
        updated = re.sub(pattern, replacement, updated)
    return updated


def convert_bash_chain_to_powershell(command: str) -> str:
    parts = [part.strip() for part in re.split(r"\s*&&\s*", command) if part.strip()]
    if len(parts) <= 1:
        return command
    guarded: list[str] = []
    for index, part in enumerate(parts):
        if index:
            guarded.append("if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }")
        guarded.append(part)
    guarded.append("if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }")
    return "; ".join(guarded)


def materialize_verify_shell(preset: dict[str, Any]) -> str:
    command = str(preset.get("VERIFY_CMD", "")).strip()
    shell = str(preset.get("VERIFY_SHELL", "direct")).strip() or "direct"
    if os.name == "nt" and shell == "bash":
        if command and not command_requires_shell(command):
            return "direct"
        return "powershell"
    return shell


def merge_local_settings(existing_text: str | None, managed: dict[str, Any]) -> dict[str, Any]:
    if not existing_text:
        return managed
    try:
        current = json.loads(existing_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Active settings.local.json is invalid JSON") from exc
    if not isinstance(current, dict):
        raise RuntimeError("Active settings.local.json must contain a JSON object")
    merged = dict(current)
    managed_permissions = managed.get("permissions", {})
    managed_allow = managed_permissions.get("allow", []) if isinstance(managed_permissions, dict) else []
    current_permissions = merged.get("permissions")
    if not isinstance(current_permissions, dict):
        current_permissions = {}
        merged["permissions"] = current_permissions
    current_allow = current_permissions.get("allow")
    if not isinstance(current_allow, list):
        current_allow = []
    combined: list[str] = []
    seen: set[str] = set()
    for item in [*current_allow, *managed_allow]:
        if not isinstance(item, str):
            continue
        if item not in seen:
            seen.add(item)
            combined.append(item)
    current_permissions["allow"] = combined
    return merged

def write_verify_config(
    dest_repo_root: Path,
    preset: dict[str, Any],
    *,
    force: bool,
    log_dir: str,
    launcher: str,
    previously_managed: set[str],
    overwrite_unmanaged: bool = False,
) -> bool:
    path = dest_repo_root / "scripts" / "verify-config.json"
    rel = "verify-config.json"
    if path.exists():
        if not force:
            if rel not in previously_managed:
                raise InitCollisionError([f"scripts/{rel}"])
            return True
        if rel not in previously_managed and not overwrite_unmanaged:
            return False
    command = materialize_verify_command(str(preset.get("VERIFY_CMD", "")).strip(), launcher)
    shell = materialize_verify_shell(preset)
    if os.name == "nt" and shell == "powershell":
        command = convert_bash_chain_to_powershell(command)
    data = {
        "VERIFY_CMD": command,
        "VERIFY_SHELL": shell,
        "PRIMARY_LOG_DIR": log_dir,
    }
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return True


def build_standard_settings(*, lang: str, syntax_enabled: bool, python_launcher: str) -> dict[str, Any]:
    hooks: dict[str, Any] = {
        "SessionStart": [
            {
                "matcher": "compact",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"echo 'Reminder: Follow .claude/CLAUDE.md and keep local workflow notes in .claude/context/ for {lang}.'",
                    }
                ],
            }
        ]
    }
    if syntax_enabled:
        hooks["PostToolUse"] = [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{python_launcher} .claude/hooks/syntax-check.py",
                    }
                ],
            }
        ]
    return {"hooks": hooks}


def build_settings(lang: str) -> dict[str, Any]:
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "compact",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"echo 'Reminder: Follow .agents/AGENTS.md and use .agents/context/* as the working memory for {lang}.'",
                        }
                    ],
                }
            ]
        }
    }


def build_local_settings(verify_cmd: str) -> dict[str, Any]:
    allow = [
        "Bash(git status:*)",
        "Bash(git diff:*)",
        "Bash(git log:*)",
        "Bash(git add:*)",
        "Bash(git commit:*)",
        "Bash(codex review:*)",
        "Bash(cat .agents/context/*)",
        "WebSearch",
        "WebFetch",
        "Bash(python scripts/run-codex-plan-review.py:*)",
        "Bash(python scripts/run-codex-impl-review.py:*)",
        "Bash(python scripts/run-codex-impl-cycle.py:*)",
        "Bash(python scripts/run-verify.py:*)",
        "Bash(python3 scripts/run-codex-plan-review.py:*)",
        "Bash(python3 scripts/run-codex-impl-review.py:*)",
        "Bash(python3 scripts/run-codex-impl-cycle.py:*)",
        "Bash(python3 scripts/run-verify.py:*)",
        "Bash(py -3 scripts/run-codex-plan-review.py:*)",
        "Bash(py -3 scripts/run-codex-impl-review.py:*)",
        "Bash(py -3 scripts/run-codex-impl-cycle.py:*)",
        "Bash(py -3 scripts/run-verify.py:*)",
    ]
    stripped_verify = verify_cmd.strip()
    if stripped_verify:
        if stripped_verify.startswith("python "):
            allow.append("Bash(python:*)")
        elif stripped_verify.startswith("python3 "):
            allow.append("Bash(python3:*)")
        elif stripped_verify.startswith("py "):
            allow.append("Bash(py:*)")
    return {"permissions": {"allow": allow}}


def build_standard_local_settings(
    *,
    is_research: bool,
    syntax_enabled: bool,
    python_launcher: str,
) -> dict[str, Any]:
    if is_research:
        allow = [
            "Bash(git status:*)",
            "Bash(git diff:*)",
            "Bash(git log:*)",
            "Bash(git add:*)",
            "Bash(git commit:*)",
            "Bash(pqa:*)",
            "Bash(paper:*)",
            "Bash(marker_single:*)",
            "Bash(bibcure:*)",
            "Bash(pandoc:*)",
            "Bash(python ~/.claude/scripts/survey-convert.py:*)",
            "Bash(python3 ~/.claude/scripts/survey-convert.py:*)",
            "Bash(py -3 ~/.claude/scripts/survey-convert.py:*)",
            "Bash(python -c:*)",
            "Bash(python3 -c:*)",
            "WebSearch",
            "WebFetch(domain:arxiv.org)",
            "WebFetch(domain:semanticscholar.org)",
            "WebFetch(domain:scholar.google.com)",
            "WebFetch(domain:openreview.net)",
            "WebFetch(domain:aclanthology.org)",
            "WebFetch(domain:papers.nips.cc)",
            "WebFetch(domain:openaccess.thecvf.com)",
            "WebFetch(domain:doi.org)",
        ]
        return {"permissions": {"allow": allow}}

    allow = [
        "Bash(git status:*)",
        "Bash(git diff:*)",
        "Bash(git log:*)",
        "Bash(git add:*)",
        "Bash(git commit:*)",
        "Bash(cat .claude/context/*)",
        "WebSearch",
        "WebFetch",
        "Bash(python scripts/run-verify.py:*)",
        "Bash(python3 scripts/run-verify.py:*)",
        "Bash(py -3 scripts/run-verify.py:*)",
    ]
    if syntax_enabled:
        syntax_allow = {
            "python": "Bash(python .claude/hooks/syntax-check.py:*)",
            "python3": "Bash(python3 .claude/hooks/syntax-check.py:*)",
            "py -3": "Bash(py -3 .claude/hooks/syntax-check.py:*)",
        }
        allow.extend(syntax_allow.values())
        launcher_key = python_launcher.strip()
        if launcher_key in syntax_allow and syntax_allow[launcher_key] not in allow:
            allow.append(syntax_allow[launcher_key])
    return {"permissions": {"allow": allow}}


def write_settings_files(
    dest_repo_root: Path,
    preset: dict[str, Any],
    *,
    force: bool,
    previously_managed: set[str],
    overwrite_unmanaged: bool = False,
) -> set[str]:
    claude_dir = dest_repo_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    settings_local_bak = claude_dir / "settings.local.json.bak"
    settings_local_active = claude_dir / "settings.local.json"
    if not force:
        collisions: list[str] = []
        for rel, path in (
            ("settings.json", settings_path),
            ("settings.local.json.bak", settings_local_bak),
            ("settings.local.json", settings_local_active),
        ):
            if path.exists() and rel not in previously_managed:
                collisions.append(f".claude/{rel}")
        if collisions:
            raise InitCollisionError(sorted(collisions))
    managed: set[str] = set()

    lang = str(preset.get("LANG", "Project"))
    verify_cmd = str(preset.get("VERIFY_CMD", "")).strip()
    settings_content = json.dumps(build_settings(lang), ensure_ascii=False, indent=2) + "\n"
    if not settings_path.exists():
        write_text(settings_path, settings_content)
        managed.add("settings.json")
    elif force and ("settings.json" in previously_managed or overwrite_unmanaged):
        write_text(settings_path, settings_content)
        managed.add("settings.json")
    elif "settings.json" in previously_managed:
        managed.add("settings.json")

    managed_local_settings = build_local_settings(verify_cmd)
    local_settings = json.dumps(managed_local_settings, ensure_ascii=False, indent=2) + "\n"
    if not settings_local_bak.exists():
        write_text(settings_local_bak, local_settings)
        managed.add("settings.local.json.bak")
    elif force and ("settings.local.json.bak" in previously_managed or overwrite_unmanaged):
        write_text(settings_local_bak, local_settings)
        managed.add("settings.local.json.bak")
    elif "settings.local.json.bak" in previously_managed:
        managed.add("settings.local.json.bak")

    if not settings_local_active.exists():
        write_text(settings_local_active, local_settings)
        managed.add("settings.local.json")
    elif force and overwrite_unmanaged:
        # --fresh: clean overwrite regardless of manifest (nuclear option).
        write_text(settings_local_active, local_settings)
        managed.add("settings.local.json")
    elif force and "settings.local.json" in previously_managed:
        merged = merge_local_settings(settings_local_active.read_text(encoding="utf-8"), managed_local_settings)
        write_text(settings_local_active, json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        managed.add("settings.local.json")
    elif "settings.local.json" in previously_managed:
        managed.add("settings.local.json")
    return managed


def write_standard_settings_files(
    dest_repo_root: Path,
    preset: dict[str, Any],
    *,
    force: bool,
    is_research: bool,
    syntax_enabled: bool,
    python_launcher: str,
    previously_managed: set[str],
    overwrite_unmanaged: bool = False,
) -> set[str]:
    claude_dir = dest_repo_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    settings_local_bak = claude_dir / "settings.local.json.bak"
    settings_local_active = claude_dir / "settings.local.json"
    if not force:
        collisions: list[str] = []
        for rel, path in (
            ("settings.json", settings_path),
            ("settings.local.json.bak", settings_local_bak),
            ("settings.local.json", settings_local_active),
        ):
            if path.exists() and rel not in previously_managed:
                collisions.append(f".claude/{rel}")
        if collisions:
            raise InitCollisionError(sorted(collisions))
    managed: set[str] = set()

    lang = str(preset.get("LANG", "Project")) if not is_research else str(preset.get("DOMAIN", "Research Survey"))
    settings_content = json.dumps(
        build_standard_settings(lang=lang, syntax_enabled=syntax_enabled, python_launcher=python_launcher),
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    if not settings_path.exists():
        write_text(settings_path, settings_content)
        managed.add("settings.json")
    elif force and ("settings.json" in previously_managed or overwrite_unmanaged):
        write_text(settings_path, settings_content)
        managed.add("settings.json")
    elif "settings.json" in previously_managed:
        managed.add("settings.json")

    managed_local_settings = build_standard_local_settings(
        is_research=is_research,
        syntax_enabled=syntax_enabled,
        python_launcher=python_launcher,
    )
    local_settings = json.dumps(managed_local_settings, ensure_ascii=False, indent=2) + "\n"
    if not settings_local_bak.exists():
        write_text(settings_local_bak, local_settings)
        managed.add("settings.local.json.bak")
    elif force and ("settings.local.json.bak" in previously_managed or overwrite_unmanaged):
        write_text(settings_local_bak, local_settings)
        managed.add("settings.local.json.bak")
    elif "settings.local.json.bak" in previously_managed:
        managed.add("settings.local.json.bak")

    if not settings_local_active.exists():
        write_text(settings_local_active, local_settings)
        managed.add("settings.local.json")
    elif force and overwrite_unmanaged:
        # --fresh: clean overwrite regardless of manifest (nuclear option).
        write_text(settings_local_active, local_settings)
        managed.add("settings.local.json")
    elif force and "settings.local.json" in previously_managed:
        merged = merge_local_settings(settings_local_active.read_text(encoding="utf-8"), managed_local_settings)
        write_text(settings_local_active, json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        managed.add("settings.local.json")
    elif "settings.local.json" in previously_managed:
        managed.add("settings.local.json")
    return managed


def update_gitignore(dest_repo_root: Path, preset: dict[str, Any], *, workflow_root: str) -> None:
    path = dest_repo_root / ".gitignore"
    if workflow_root == ".agents":
        entries = [
            ".agents/context/",
            ".agents/reviews/",
            ".agents/logs/",
            ".agents/context/_codex_input.tmp",
            ".codex_tmp/",
            ".claude/settings.local.json",
        ]
    else:
        entries = [
            ".codex_tmp/",
            ".claude/context/",
            ".claude/settings.local.json",
            ".claude/logs/verify/",
        ]
    extra = str(preset.get("GITIGNORE_ENTRIES", "")).strip()
    if extra and extra.lower() != "none":
        entries.extend(entry.strip() for entry in extra.split(",") if entry.strip())

    existing = []
    if path.exists():
        existing = path.read_text(encoding="utf-8").splitlines()
    managed_obsolete = {".agents/"} if workflow_root == ".agents" else set()
    merged = [line for line in existing if line not in managed_obsolete]
    existing_set = set(merged)
    for entry in entries:
        if entry not in existing_set:
            merged.append(entry)
            existing_set.add(entry)
    write_text(path, ("\n".join(merged).rstrip() + "\n") if merged else "")


def get_file_extensions_from_patterns(patterns: str) -> list[str]:
    extensions: list[str] = []
    seen: set[str] = set()
    for raw_pattern in patterns.split(","):
        pattern = raw_pattern.strip()
        if not pattern or "." not in pattern:
            continue
        suffix = pattern.rsplit(".", 1)[-1].strip()
        if not suffix or "*" in suffix or "/" in suffix:
            continue
        extension = f".{suffix.lower()}"
        if extension not in seen:
            seen.add(extension)
            extensions.append(extension)
    return extensions


def write_standard_hook_and_docs(
    dest_repo_root: Path,
    preset: dict[str, Any],
    *,
    force: bool,
    is_research: bool,
    workflow_only: bool,
    previously_managed: set[str],
    overwrite_unmanaged: bool = False,
) -> set[str]:
    managed: set[str] = set()
    # Determine whether this run would write the syntax-check hook so the
    # collision pre-check can limit itself to paths actually owned by the
    # selected preset.  Only standard (non-research) templates with
    # SYNTAX_CHECK_ENABLED=true and matching extensions generate the hook.
    launcher_probe = str(preset.get("PYTHON_LAUNCHER", "")).strip()
    syntax_cmd_probe = (
        materialize_verify_command(str(preset.get("SYNTAX_CHECK_CMD", "")).strip(), launcher_probe)
        if launcher_probe
        else str(preset.get("SYNTAX_CHECK_CMD", "")).strip()
    )
    syntax_enabled_probe = bool(preset.get("SYNTAX_CHECK_ENABLED", False)) and bool(syntax_cmd_probe)
    extensions_probe = get_file_extensions_from_patterns(str(preset.get("FILE_PATTERNS", "")).strip())
    hook_will_be_written = (not is_research) and syntax_enabled_probe and bool(extensions_probe)

    if not force:
        # Pre-check collisions for the paths this helper actually writes.
        collisions: list[str] = []
        claude_md_path_check = dest_repo_root / ".claude" / "CLAUDE.md"
        if claude_md_path_check.exists() and "CLAUDE.md" not in previously_managed:
            collisions.append(".claude/CLAUDE.md")
        if hook_will_be_written:
            hook_path_check = dest_repo_root / ".claude" / "hooks" / "syntax-check.py"
            if hook_path_check.exists() and "hooks/syntax-check.py" not in previously_managed:
                collisions.append(".claude/hooks/syntax-check.py")
        if collisions:
            raise InitCollisionError(sorted(collisions))
    if is_research:
        domain = str(preset.get("DOMAIN", "Research Survey"))
        key_venues = str(preset.get("KEY_VENUES", "")).strip()
        survey_rules = str(preset.get("SURVEY_RULES", "")).strip()
        claude_md = f"""# Research Survey — {domain}

## Domain

{domain}

## Key Venues

{key_venues}

## Survey Methodology Rules

{survey_rules}

## Tools

推奨 CLI ツール（全てオプション）:
- `pip install paper-qa>=5 arxiv-dl marker-pdf semanticscholar bibcure`
- Pandoc: `winget install --id JohnMacFarlane.Pandoc`

ツール検出: `/check-tools`

## Workflow

`/scope` → `/search` → `/read` → `/outline` → `/draft` → `/review` → `/convert`

## Commit Messages

- 1行目 (subject): 英語。imperative form (e.g. `Add survey section on X`)
- 2行目: 空行
- 3行目以降 (body): 日本語可。変更理由・詳細を記述
        """
        claude_md_path = dest_repo_root / ".claude" / "CLAUDE.md"
        if not claude_md_path.exists():
            write_text(claude_md_path, claude_md.rstrip() + "\n")
            managed.add("CLAUDE.md")
        elif force and ("CLAUDE.md" in previously_managed or overwrite_unmanaged):
            write_text(claude_md_path, claude_md.rstrip() + "\n")
            managed.add("CLAUDE.md")
        elif "CLAUDE.md" in previously_managed:
            managed.add("CLAUDE.md")
        return managed

    launcher = str(preset.get("PYTHON_LAUNCHER", "")).strip()
    syntax_cmd = materialize_verify_command(str(preset.get("SYNTAX_CHECK_CMD", "")).strip(), launcher) if launcher else str(preset.get("SYNTAX_CHECK_CMD", "")).strip()
    syntax_enabled = bool(preset.get("SYNTAX_CHECK_ENABLED", False)) and bool(syntax_cmd)
    file_patterns = str(preset.get("FILE_PATTERNS", "")).strip()
    extensions = get_file_extensions_from_patterns(file_patterns)
    lang = str(preset.get("LANG", "Project"))
    verify_cmd = materialize_verify_command(str(preset.get("VERIFY_CMD", "")).strip(), launcher) if launcher else str(preset.get("VERIFY_CMD", "")).strip()
    lang_rules = str(preset.get("LANG_RULES", "")).strip()

    if syntax_enabled and extensions:
        hook_content = f"""#!/usr/bin/env python3
\"\"\"PostToolUse hook: syntax check for {lang} files.\"\"\"
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys

EXTENSIONS = {json.dumps(extensions, ensure_ascii=False)}
SYNTAX_CMD = {json.dumps(syntax_cmd, ensure_ascii=False)}
FILE_PLACEHOLDER = "$FILE"


def normalize_arg(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        return token[1:-1]
    return token


def build_command(file_path: str) -> list[str]:
    parts = shlex.split(SYNTAX_CMD, posix=(os.name != "nt"))
    command: list[str] = []
    replaced = False
    for part in parts:
        normalized = normalize_arg(part)
        if normalized == FILE_PLACEHOLDER:
            command.append(file_path)
            replaced = True
        else:
            command.append(normalized)
    if FILE_PLACEHOLDER in SYNTAX_CMD and not replaced:
        raise SystemExit("Syntax check command did not preserve the $FILE placeholder as an argv token.")
    return command


def main() -> None:
    data = json.load(sys.stdin)
    file_path = data.get("tool_input", {{}}).get("file_path", "")
    if not file_path:
        return
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in EXTENSIONS:
        return
    result = subprocess.run(build_command(file_path), capture_output=True, text=True)
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        print(output, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
"""
        hook_path = dest_repo_root / ".claude" / "hooks" / "syntax-check.py"
        if not hook_path.exists():
            write_text(hook_path, hook_content)
            managed.add("hooks/syntax-check.py")
        elif force and ("hooks/syntax-check.py" in previously_managed or overwrite_unmanaged):
            write_text(hook_path, hook_content)
            managed.add("hooks/syntax-check.py")
        elif "hooks/syntax-check.py" in previously_managed:
            managed.add("hooks/syntax-check.py")

    failure_report = """# Failure Report

## Summary

- Task:
- Failure pattern:
- Attempted command:
- Exit code:
- Latest status file: `.claude/logs/verify/latest.status.json`
- Latest log file: `.claude/logs/verify/latest.log`

## Latest Status Snapshot

```json
{}
```

## Latest Log Tail

```text
(paste the last 50 lines from .claude/logs/verify/latest.log here)
```

## Notes

- What was tried:
- Suspected root cause:
- Next decision needed:
"""
    failure_report_path = dest_repo_root / ".claude" / "context" / "failure_report.md"
    if not workflow_only and not failure_report_path.exists():
        write_text(failure_report_path, failure_report)

    claude_md = f"""# {lang} Project

## Language

{lang}。構文バージョンを混同しないこと。

## Coding Rules

{lang_rules}

## Commit Messages

- 1行目 (subject): 英語。imperative form (e.g. `Fix authentication bug`)
- 2行目: 空行
- 3行目以降 (body): 日本語可。変更理由・詳細を記述

## Testing

検証コマンド: `{verify_cmd}`
"""
    claude_md_path = dest_repo_root / ".claude" / "CLAUDE.md"
    if not claude_md_path.exists():
        write_text(claude_md_path, claude_md.rstrip() + "\n")
        managed.add("CLAUDE.md")
    elif force and ("CLAUDE.md" in previously_managed or overwrite_unmanaged):
        write_text(claude_md_path, claude_md.rstrip() + "\n")
        managed.add("CLAUDE.md")
    elif "CLAUDE.md" in previously_managed:
        managed.add("CLAUDE.md")
    return managed


def copy_named_runner_files(
    source_scripts_dir: Path,
    dest_repo_root: Path,
    names: tuple[str, ...],
    *,
    force: bool,
    overwrite_unmanaged: bool = False,
) -> set[str]:
    dest_scripts_dir = dest_repo_root / "scripts"
    dest_scripts_dir.mkdir(parents=True, exist_ok=True)
    expected: set[str] = set()
    manifest_path = dest_scripts_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = (
        read_workflow_manifest_tolerant(manifest_path)
        if overwrite_unmanaged
        else read_workflow_manifest(manifest_path)
    )
    if not force:
        collisions = [
            f"scripts/{name}"
            for name in names
            if (dest_scripts_dir / name).exists() and name not in previously_managed
        ]
        if collisions:
            raise InitCollisionError(sorted(collisions))
    for name in names:
        src = source_scripts_dir / name
        if not src.is_file():
            raise FileNotFoundError(f"Required runner not found: {src}")
        dst = dest_scripts_dir / name
        if dst.exists():
            if not force:
                if name in previously_managed:
                    expected.add(name)
                continue
            if name not in previously_managed and not overwrite_unmanaged:
                continue
        shutil.copy2(src, dst)
        expected.add(name)
    return expected


def prune_retired_runner_files(
    dest_repo_root: Path,
    names: tuple[str, ...],
    *,
    force: bool,
    expected: set[str],
    preset_name: str | None = None,
    template_name: str | None = None,
    overwrite_unmanaged: bool = False,
) -> None:
    scripts_dir = dest_repo_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = scripts_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = (
        read_workflow_manifest_tolerant(manifest_path)
        if overwrite_unmanaged
        else read_workflow_manifest(manifest_path)
    )
    if force:
        retired = set(names)
        for name in names:
            if name in expected or name not in previously_managed:
                continue
            path = scripts_dir / name
            if path.exists():
                path.unlink()
    manifest_entries = set(expected)
    if not force:
        manifest_entries.update(
            entry for entry in previously_managed if (scripts_dir / entry).exists()
        )
    write_workflow_manifest(
        manifest_path,
        manifest_entries,
        preset=preset_name,
        template=template_name,
    )


def initialize_codex_main(
    preset_name: str,
    *,
    force: bool,
    workflow_only: bool,
    skills_only: bool,
    overwrite_unmanaged: bool = False,
) -> None:
    template_root = discover_template_root("codex-main")
    source_scripts_dir = discover_script_source_dir()
    presets = load_presets(template_root)
    if preset_name not in presets:
        raise KeyError(f"Unknown preset '{preset_name}'. Available: {', '.join(sorted(presets))}")
    preset = dict(presets[preset_name])
    if not isinstance(preset, dict):
        raise ValueError(f"Invalid preset '{preset_name}'")
    repo_root = Path.cwd().resolve()
    if skills_only:
        require_existing_codex_runners(repo_root)
    launcher = (
        infer_existing_python_launcher(repo_root) or default_portable_python_launcher()
        if skills_only
        else discover_portable_python_launcher()
    )
    preset["PYTHON_LAUNCHER"] = launcher
    preset["VERIFY_CMD"] = materialize_verify_command(str(preset.get("VERIFY_CMD", "")).strip(), launcher)
    # In --fresh recovery mode (overwrite_unmanaged=True), swallow manifest parse
    # errors so a corrupt manifest does not block reinitialization.
    _read_manifest = read_workflow_manifest_tolerant if overwrite_unmanaged else read_workflow_manifest
    dest_agents_dir = repo_root / ".agents"
    workflow_manifest = _read_manifest(dest_agents_dir / WORKFLOW_MANIFEST_NAME)
    expected_workflow = copy_template_tree(
        template_root / ".agents",
        dest_agents_dir,
        preset,
        force=force,
        workflow_only=workflow_only,
        skills_only=skills_only,
        workflow_root=".agents",
        previously_managed=workflow_manifest,
        overwrite_unmanaged=overwrite_unmanaged,
    )
    seed_context_files(dest_agents_dir, force=force, workflow_only=workflow_only, skills_only=skills_only)
    if build_legacy_impl_review_prompt(
        dest_agents_dir,
        force=force,
        previously_managed=workflow_manifest,
        skills_only=skills_only,
        overwrite_unmanaged=overwrite_unmanaged,
    ):
        expected_workflow.add("prompts/codex_impl_review.md")
    prune_workflow_tree(
        dest_agents_dir,
        expected=expected_workflow,
        force=force,
        workflow_only=workflow_only,
        skills_only=skills_only,
        workflow_root=".agents",
        preset_name=preset_name,
        template_name="codex-main",
        overwrite_unmanaged=overwrite_unmanaged,
    )
    if not skills_only:
        expected_scripts = copy_runner_files(
            source_scripts_dir,
            repo_root,
            force=force,
            overwrite_unmanaged=overwrite_unmanaged,
        )
        if write_verify_config(
            repo_root,
            preset,
            force=force,
            log_dir=".agents/logs/verify",
            launcher=launcher,
            previously_managed=_read_manifest((repo_root / "scripts" / WORKFLOW_MANIFEST_NAME)),
            overwrite_unmanaged=overwrite_unmanaged,
        ):
            expected_scripts.add("verify-config.json")
        prune_retired_runner_files(
            repo_root,
            RETIRED_CODEX_RUNNERS,
            force=force,
            expected=expected_scripts,
            preset_name=preset_name,
            template_name="codex-main",
            overwrite_unmanaged=overwrite_unmanaged,
        )
        claude_manifest_path = repo_root / ".claude" / WORKFLOW_MANIFEST_NAME
        previous_claude_manifest = _read_manifest(claude_manifest_path)
        settings_entries = {"settings.json", "settings.local.json.bak", "settings.local.json"}
        if force:
            prune_manifest_owned_paths(
                repo_root / ".claude",
                previous_claude_manifest,
                keep=settings_entries,
            )
        managed_claude = write_settings_files(
            repo_root,
            preset,
            force=force,
            previously_managed=previous_claude_manifest,
            overwrite_unmanaged=overwrite_unmanaged,
        )
        write_workflow_manifest(
            claude_manifest_path,
            managed_claude,
            preset=preset_name,
            template="codex-main",
        )
        update_gitignore(repo_root, preset, workflow_root=".agents")


def initialize_standard_template(
    template_name: str,
    preset_name: str,
    *,
    force: bool,
    workflow_only: bool,
    overwrite_unmanaged: bool = False,
) -> None:
    template_root = discover_template_root(template_name)
    source_scripts_dir = discover_script_source_dir()
    presets = load_presets(template_root)
    if preset_name not in presets:
        raise KeyError(f"Unknown preset '{preset_name}'. Available: {', '.join(sorted(presets))}")
    preset = dict(presets[preset_name])
    if not isinstance(preset, dict):
        raise ValueError(f"Invalid preset '{preset_name}'")
    launcher = discover_portable_python_launcher()
    preset["PYTHON_LAUNCHER"] = launcher
    preset["VERIFY_CMD"] = materialize_verify_command(str(preset.get("VERIFY_CMD", "")).strip(), launcher)

    repo_root = Path.cwd().resolve()
    # In --fresh recovery mode, swallow manifest parse errors.
    _read_manifest = read_workflow_manifest_tolerant if overwrite_unmanaged else read_workflow_manifest
    dest_claude_dir = repo_root / ".claude"
    workflow_manifest = _read_manifest(dest_claude_dir / WORKFLOW_MANIFEST_NAME)
    expected_workflow = copy_template_tree(
        template_root / ".claude",
        dest_claude_dir,
        preset,
        force=force,
        workflow_only=workflow_only,
        skills_only=False,
        workflow_root=".claude",
        previously_managed=workflow_manifest,
        overwrite_unmanaged=overwrite_unmanaged,
    )
    seed_standard_context(dest_claude_dir, force=force, workflow_only=workflow_only)
    expected_scripts = copy_named_runner_files(
        source_scripts_dir,
        repo_root,
        ("run-verify.py",),
        force=force,
        overwrite_unmanaged=overwrite_unmanaged,
    )
    if write_verify_config(
        repo_root,
        preset,
        force=force,
        log_dir=".claude/logs/verify",
        launcher=launcher,
        previously_managed=_read_manifest((repo_root / "scripts" / WORKFLOW_MANIFEST_NAME)),
        overwrite_unmanaged=overwrite_unmanaged,
    ):
        expected_scripts.add("verify-config.json")
    prune_retired_runner_files(
        repo_root,
        RETIRED_STANDARD_RUNNERS + CODEX_ONLY_RUNNERS,
        force=force,
        expected=expected_scripts,
        overwrite_unmanaged=overwrite_unmanaged,
        preset_name=preset_name,
        template_name=template_name,
    )
    is_research = template_name == "research-survey"
    syntax_enabled = bool(preset.get("SYNTAX_CHECK_ENABLED", False)) and bool(str(preset.get("SYNTAX_CHECK_CMD", "")).strip())
    expected_workflow.update(
        write_standard_settings_files(
        repo_root,
        preset,
        force=force,
        is_research=is_research,
        syntax_enabled=syntax_enabled,
        python_launcher=launcher,
        previously_managed=workflow_manifest,
        overwrite_unmanaged=overwrite_unmanaged,
        )
    )
    expected_workflow.update(
        write_standard_hook_and_docs(
            repo_root,
            preset,
            force=force,
            is_research=is_research,
            workflow_only=workflow_only,
            previously_managed=workflow_manifest,
            overwrite_unmanaged=overwrite_unmanaged,
        )
    )
    prune_workflow_tree(
        dest_claude_dir,
        expected=expected_workflow,
        force=force,
        workflow_only=workflow_only,
        skills_only=False,
        workflow_root=".claude",
        preset_name=preset_name,
        template_name=template_name,
        overwrite_unmanaged=overwrite_unmanaged,
    )
    update_gitignore(repo_root, preset, workflow_root=".claude")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    repo_root = Path.cwd()
    # --fresh is the recovery path for broken installs — never let a malformed
    # manifest block it.  For other modes the manifest is authoritative and
    # parse errors surface to the user.  When --fresh succeeds in parsing the
    # manifest we keep the tags so bare `--fresh` can still recover the same
    # template/preset and so the cross-template guard stays active.
    try:
        active_template, manifest_preset, legacy_uninferable = detect_active_template(repo_root)
    except RuntimeError as exc:
        if args.fresh:
            active_template, manifest_preset, legacy_uninferable = None, None, False
        else:
            print(
                f"ERROR: {exc}\n"
                "If the manifest is corrupted, re-run with --fresh to reinitialize "
                "from scratch.",
                file=sys.stderr,
            )
            return 1

    explicit_template = args.template

    # Legacy manifest that we cannot classify requires an explicit -t to disambiguate
    # (migrates the manifest on this run).
    if legacy_uninferable and explicit_template is None:
        print(
            "ERROR: legacy manifest detected but template cannot be inferred. "
            "Please run with '-t <template> <preset>' once to migrate the manifest.",
            file=sys.stderr,
        )
        return 1

    # Determine mode
    if args.fresh:
        mode = "fresh"
    elif args.update:
        if active_template is None:
            print(
                "ERROR: --update requires an existing scaffold (no manifest found).",
                file=sys.stderr,
            )
            return 1
        mode = "update"
    elif active_template is not None:
        mode = "update"  # smart routing
    else:
        mode = "init"

    # Resolve template (preference: explicit -t > manifest > preset inference > default)
    if explicit_template is not None:
        template = explicit_template
    elif active_template is not None:
        template = active_template
    elif args.preset and args.preset.startswith("survey-"):
        template = "research-survey"
    else:
        template = "project-init"

    # Cross-template switch is not supported; require manual rm -rf for switching
    if active_template is not None and active_template != template:
        print(
            "ERROR: cross-template switch is not supported.\n"
            f"  Active template: {active_template}\n"
            f"  Requested template: {template}\n"
            "To switch, back up context files you want to keep and then run:\n"
            "  rm -rf .claude .agents\n"
            f"  /init-project -t {template} <preset>",
            file=sys.stderr,
        )
        return 1

    # Resolve preset
    preset_name: str | None = args.preset or manifest_preset
    if not preset_name:
        print("ERROR: preset is required", file=sys.stderr)
        return 1

    # Preset mismatch detection (update mode only; fresh implies overwrite intent)
    if (
        mode == "update"
        and args.preset is not None
        and manifest_preset is not None
        and args.preset != manifest_preset
        and not args.accept_preset_change
    ):
        print(
            f"WARNING: preset mismatch. Manifest records '{manifest_preset}', "
            f"but '{args.preset}' was requested.\n"
            "Re-run with --accept-preset-change to confirm the change "
            "(or --fresh to reinitialize).",
            file=sys.stderr,
        )
        return 3  # dedicated exit code for preset mismatch (avoid argparse error code 2)

    # Map mode to initialize_* parameters.
    # - init (no flag, no manifest): force=False → skip existing.
    # - update (smart or --update): force=True + workflow_only=True → refresh managed,
    #   preserve context/. overwrite_unmanaged=False → keep user-owned files at template paths.
    # - fresh (--fresh): force=True + workflow_only=False → overwrite all, including
    #   non-managed files at template paths (nuclear re-init).
    if mode == "fresh":
        force = True
        workflow_only = False
        overwrite_unmanaged = True
    elif mode == "update":
        force = True
        workflow_only = True
        overwrite_unmanaged = False
    else:  # init
        force = False
        workflow_only = False
        overwrite_unmanaged = False

    try:
        if template == "codex-main":
            initialize_codex_main(
                preset_name,
                force=force,
                workflow_only=workflow_only,
                skills_only=False,
                overwrite_unmanaged=overwrite_unmanaged,
            )
            print(f"Initialized codex-main preset: {preset_name}")
            print("Created/updated: .agents/, .claude/settings.json, .claude/settings.local.json(.bak), scripts/*.py, .gitignore")
        else:
            initialize_standard_template(
                template,
                preset_name,
                force=force,
                workflow_only=workflow_only,
                overwrite_unmanaged=overwrite_unmanaged,
            )
            print(f"Initialized template {template}: {preset_name}")
            print("Created/updated: .claude/, scripts/run-verify.py, scripts/verify-config.json, .gitignore")
    except InitCollisionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
