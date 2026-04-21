#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize the current repository with the codex-main Python-first scaffold.")
    parser.add_argument("--codex-main", action="store_true")
    parser.add_argument("-t", "--template")
    parser.add_argument("preset", nargs="?")
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("--workflow-only", action="store_true")
    parser.add_argument("--skills-only", action="store_true")
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
) -> set[str]:
    previously_managed = previously_managed or set()
    expected: set[str] = set()
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
            if rel not in previously_managed:
                continue
        try:
            content = substitute_content(read_text(src), preset)
            write_text(dst, content)
        except UnicodeDecodeError:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        expected.add(rel)
    return expected


def read_workflow_manifest(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    try:
        data = json.loads(read_text(path))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Unable to read workflow manifest: {path}") from exc
    entries = data.get("managed", [])
    if not isinstance(entries, list):
        raise RuntimeError(f"Workflow manifest has invalid structure: {path}")
    return {str(item) for item in entries if isinstance(item, str) and item}


def write_workflow_manifest(path: Path, entries: set[str]) -> None:
    write_text(path, json.dumps({"managed": sorted(entries)}, ensure_ascii=False, indent=2) + "\n")


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
) -> None:
    manifest_path = dest_workflow_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = read_workflow_manifest(manifest_path)
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
    write_workflow_manifest(manifest_path, manifest_entries)


def build_legacy_impl_review_prompt(
    dest_agents_dir: Path,
    *,
    force: bool,
    previously_managed: set[str],
    skills_only: bool,
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
            return legacy_rel in previously_managed
        if legacy_rel not in previously_managed:
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


def copy_runner_files(source_scripts_dir: Path, dest_repo_root: Path, *, force: bool) -> set[str]:
    dest_scripts_dir = dest_repo_root / "scripts"
    dest_scripts_dir.mkdir(parents=True, exist_ok=True)
    expected: set[str] = set()
    manifest_path = dest_scripts_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = read_workflow_manifest(manifest_path)
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
            if name not in previously_managed:
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
) -> bool:
    path = dest_repo_root / "scripts" / "verify-config.json"
    rel = "verify-config.json"
    if path.exists():
        if not force:
            return rel in previously_managed
        if rel not in previously_managed:
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
            "Bash(bash ~/.claude/scripts/survey-convert.sh:*)",
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
) -> set[str]:
    claude_dir = dest_repo_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    settings_local_bak = claude_dir / "settings.local.json.bak"
    settings_local_active = claude_dir / "settings.local.json"
    managed: set[str] = set()

    lang = str(preset.get("LANG", "Project"))
    verify_cmd = str(preset.get("VERIFY_CMD", "")).strip()
    if not settings_path.exists() or (force and "settings.json" in previously_managed):
        write_text(settings_path, json.dumps(build_settings(lang), ensure_ascii=False, indent=2) + "\n")
        managed.add("settings.json")
    elif settings_path.exists() and "settings.json" in previously_managed:
        managed.add("settings.json")

    managed_local_settings = build_local_settings(verify_cmd)
    local_settings = json.dumps(managed_local_settings, ensure_ascii=False, indent=2) + "\n"
    if not settings_local_bak.exists() or (force and "settings.local.json.bak" in previously_managed):
        write_text(settings_local_bak, local_settings)
        managed.add("settings.local.json.bak")
    elif settings_local_bak.exists() and "settings.local.json.bak" in previously_managed:
        managed.add("settings.local.json.bak")

    if settings_local_active.exists() and force and "settings.local.json" in previously_managed:
        merged = merge_local_settings(settings_local_active.read_text(encoding="utf-8"), managed_local_settings)
        write_text(settings_local_active, json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        managed.add("settings.local.json")
    elif settings_local_active.exists() and "settings.local.json" in previously_managed:
        managed.add("settings.local.json")
    elif not settings_local_active.exists():
        write_text(settings_local_active, local_settings)
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
) -> set[str]:
    claude_dir = dest_repo_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    settings_local_bak = claude_dir / "settings.local.json.bak"
    settings_local_active = claude_dir / "settings.local.json"
    managed: set[str] = set()

    lang = str(preset.get("LANG", "Project")) if not is_research else str(preset.get("DOMAIN", "Research Survey"))
    settings_content = json.dumps(
        build_standard_settings(lang=lang, syntax_enabled=syntax_enabled, python_launcher=python_launcher),
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    if not settings_path.exists() or (force and "settings.json" in previously_managed):
        write_text(settings_path, settings_content)
        managed.add("settings.json")
    elif settings_path.exists() and "settings.json" in previously_managed:
        managed.add("settings.json")

    managed_local_settings = build_standard_local_settings(
        is_research=is_research,
        syntax_enabled=syntax_enabled,
        python_launcher=python_launcher,
    )
    local_settings = json.dumps(managed_local_settings, ensure_ascii=False, indent=2) + "\n"
    if not settings_local_bak.exists() or (force and "settings.local.json.bak" in previously_managed):
        write_text(settings_local_bak, local_settings)
        managed.add("settings.local.json.bak")
    elif settings_local_bak.exists() and "settings.local.json.bak" in previously_managed:
        managed.add("settings.local.json.bak")

    if settings_local_active.exists() and force and "settings.local.json" in previously_managed:
        merged = merge_local_settings(settings_local_active.read_text(encoding="utf-8"), managed_local_settings)
        write_text(settings_local_active, json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        managed.add("settings.local.json")
    elif settings_local_active.exists() and "settings.local.json" in previously_managed:
        managed.add("settings.local.json")
    elif not settings_local_active.exists():
        write_text(settings_local_active, local_settings)
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
) -> set[str]:
    managed: set[str] = set()
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
        if not claude_md_path.exists() or force and "CLAUDE.md" in previously_managed:
            write_text(claude_md_path, claude_md.rstrip() + "\n")
            managed.add("CLAUDE.md")
        elif claude_md_path.exists() and "CLAUDE.md" in previously_managed:
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
        if not hook_path.exists() or force and "hooks/syntax-check.py" in previously_managed:
            write_text(hook_path, hook_content)
            managed.add("hooks/syntax-check.py")
        elif hook_path.exists() and "hooks/syntax-check.py" in previously_managed:
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
    if not claude_md_path.exists() or force and "CLAUDE.md" in previously_managed:
        write_text(claude_md_path, claude_md.rstrip() + "\n")
        managed.add("CLAUDE.md")
    elif claude_md_path.exists() and "CLAUDE.md" in previously_managed:
        managed.add("CLAUDE.md")
    return managed


def copy_named_runner_files(source_scripts_dir: Path, dest_repo_root: Path, names: tuple[str, ...], *, force: bool) -> set[str]:
    dest_scripts_dir = dest_repo_root / "scripts"
    dest_scripts_dir.mkdir(parents=True, exist_ok=True)
    expected: set[str] = set()
    manifest_path = dest_scripts_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = read_workflow_manifest(manifest_path)
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
            if name not in previously_managed:
                continue
        shutil.copy2(src, dst)
        expected.add(name)
    return expected


def prune_retired_runner_files(dest_repo_root: Path, names: tuple[str, ...], *, force: bool, expected: set[str]) -> None:
    scripts_dir = dest_repo_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = scripts_dir / WORKFLOW_MANIFEST_NAME
    previously_managed = read_workflow_manifest(manifest_path)
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
    write_workflow_manifest(manifest_path, manifest_entries)


def initialize_codex_main(preset_name: str, *, force: bool, workflow_only: bool, skills_only: bool) -> None:
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
    dest_agents_dir = repo_root / ".agents"
    workflow_manifest = read_workflow_manifest(dest_agents_dir / WORKFLOW_MANIFEST_NAME)
    expected_workflow = copy_template_tree(
        template_root / ".agents",
        dest_agents_dir,
        preset,
        force=force,
        workflow_only=workflow_only,
        skills_only=skills_only,
        workflow_root=".agents",
        previously_managed=workflow_manifest,
    )
    seed_context_files(dest_agents_dir, force=force, workflow_only=workflow_only, skills_only=skills_only)
    if build_legacy_impl_review_prompt(
        dest_agents_dir,
        force=force,
        previously_managed=workflow_manifest,
        skills_only=skills_only,
    ):
        expected_workflow.add("prompts/codex_impl_review.md")
    prune_workflow_tree(
        dest_agents_dir,
        expected=expected_workflow,
        force=force,
        workflow_only=workflow_only,
        skills_only=skills_only,
        workflow_root=".agents",
    )
    if not skills_only:
        expected_scripts = copy_runner_files(source_scripts_dir, repo_root, force=force)
        if write_verify_config(
            repo_root,
            preset,
            force=force,
            log_dir=".agents/logs/verify",
            launcher=launcher,
            previously_managed=read_workflow_manifest((repo_root / "scripts" / WORKFLOW_MANIFEST_NAME)),
        ):
            expected_scripts.add("verify-config.json")
        prune_retired_runner_files(repo_root, RETIRED_CODEX_RUNNERS, force=force, expected=expected_scripts)
        claude_manifest_path = repo_root / ".claude" / WORKFLOW_MANIFEST_NAME
        previous_claude_manifest = read_workflow_manifest(claude_manifest_path)
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
        )
        write_workflow_manifest(claude_manifest_path, managed_claude)
        update_gitignore(repo_root, preset, workflow_root=".agents")


def initialize_standard_template(template_name: str, preset_name: str, *, force: bool, workflow_only: bool) -> None:
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
    dest_claude_dir = repo_root / ".claude"
    workflow_manifest = read_workflow_manifest(dest_claude_dir / WORKFLOW_MANIFEST_NAME)
    expected_workflow = copy_template_tree(
        template_root / ".claude",
        dest_claude_dir,
        preset,
        force=force,
        workflow_only=workflow_only,
        skills_only=False,
        workflow_root=".claude",
        previously_managed=workflow_manifest,
    )
    seed_standard_context(dest_claude_dir, force=force, workflow_only=workflow_only)
    expected_scripts = copy_named_runner_files(source_scripts_dir, repo_root, ("run-verify.py",), force=force)
    if write_verify_config(
        repo_root,
        preset,
        force=force,
        log_dir=".claude/logs/verify",
        launcher=launcher,
        previously_managed=read_workflow_manifest((repo_root / "scripts" / WORKFLOW_MANIFEST_NAME)),
    ):
        expected_scripts.add("verify-config.json")
    prune_retired_runner_files(
        repo_root,
        RETIRED_STANDARD_RUNNERS + CODEX_ONLY_RUNNERS,
        force=force,
        expected=expected_scripts,
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
        )
    )
    prune_workflow_tree(
        dest_claude_dir,
        expected=expected_workflow,
        force=force,
        workflow_only=workflow_only,
        skills_only=False,
        workflow_root=".claude",
    )
    update_gitignore(repo_root, preset, workflow_root=".claude")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.codex_main and args.template:
        print("ERROR: use either --codex-main or --template/-t, not both", file=sys.stderr)
        return 1
    if not args.preset:
        print("ERROR: preset is required", file=sys.stderr)
        return 1

    try:
        if args.codex_main:
            initialize_codex_main(
                args.preset,
                force=args.force,
                workflow_only=args.workflow_only,
                skills_only=args.skills_only,
            )
            print(f"Initialized codex-main preset: {args.preset}")
            print("Created/updated: .agents/, .claude/settings.json, .claude/settings.local.json(.bak), scripts/*.py, .gitignore")
        elif args.template:
            initialize_standard_template(
                args.template,
                args.preset,
                force=args.force,
                workflow_only=args.workflow_only,
            )
            print(f"Initialized template {args.template}: {args.preset}")
            print("Created/updated: .claude/, scripts/run-verify.py, scripts/verify-config.json, .gitignore")
        else:
            print("ERROR: specify --codex-main or --template/-t", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
