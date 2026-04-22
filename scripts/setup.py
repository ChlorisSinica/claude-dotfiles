#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fix_codex_plugin_prompts import fix_plugin_prompts_if_available


IGNORE_NAMES = {"__pycache__", "_legacy"}
MANIFEST_NAME = ".claude-dotfiles-managed.json"
SOURCE_METADATA_NAME = ".claude-dotfiles-source.json"
PRE_MANIFEST_RETIREMENTS: dict[str, set[Path]] = {
    "commands": {
        Path("update-skills.md"),
    },
    "templates": set(),
    "scripts": {
        Path("init-project.ps1"),
        Path("init-project.sh"),
        Path("run-codex-plan-review.ps1"),
        Path("run-codex-impl-review.ps1"),
        Path("run-verify.ps1"),
        Path("run-verify.sh"),
        Path("fix-codex-plugin-prompts.ps1"),
        Path("survey-convert.sh"),
    },
    "codex-skills": set(),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Claude Code dotfiles and optional Codex skills without requiring shell wrappers.")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite managed files that already exist.")
    parser.add_argument("--codex", action="store_true", help="Also install Codex global skills into ~/.codex/skills.")
    parser.add_argument("--statusline", action="store_true", help="Also install the Claude Code custom statusline.")
    parser.add_argument("--source-root", help="Override the source repo root. Defaults to the current script's repo.")
    parser.add_argument("--claude-dir", help="Override ~/.claude destination.")
    parser.add_argument("--codex-dir", help="Override ~/.codex destination.")
    return parser.parse_args(argv)


def script_root() -> Path:
    return Path(__file__).resolve().parent


def repo_root_from_script() -> Path:
    return script_root().parent


def looks_like_source_repo_root(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "commands").is_dir()
        and (path / "templates").is_dir()
        and (path / "scripts").is_dir()
        and (path / "codex").is_dir()
        and (path / "dotfiles").is_dir()
    )


def read_source_metadata(claude_dir: Path) -> Path | None:
    metadata_path = claude_dir / SOURCE_METADATA_NAME
    data = read_json_file(metadata_path)
    source_root = data.get("source_root")
    if not isinstance(source_root, str) or not source_root.strip():
        return None
    candidate = Path(source_root).expanduser().resolve()
    if looks_like_source_repo_root(candidate):
        return candidate
    return None


def write_source_metadata(claude_dir: Path, repo_root: Path) -> None:
    write_json_file(
        claude_dir / SOURCE_METADATA_NAME,
        {"source_root": str(repo_root.resolve())},
    )


def resolve_repo_root(source_root: str | None, *, claude_dir: Path | None = None) -> Path:
    if source_root:
        candidate = Path(source_root).expanduser().resolve()
        if looks_like_source_repo_root(candidate):
            return candidate
        raise FileNotFoundError(f"Specified source root does not look like claude-dotfiles: {candidate}")
    env_root = os.environ.get("CLAUDE_DOTFILES_SOURCE_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if looks_like_source_repo_root(candidate):
            return candidate
    if claude_dir:
        metadata_root = read_source_metadata(claude_dir)
        if metadata_root is not None:
            return metadata_root
    home_candidate = resolve_home_dir() / "claude-dotfiles"
    if looks_like_source_repo_root(home_candidate):
        return home_candidate.resolve()
    script_root_candidate = repo_root_from_script()
    if looks_like_source_repo_root(script_root_candidate):
        return script_root_candidate
    raise FileNotFoundError(
        "Could not locate the claude-dotfiles source repo. Pass --source-root, set CLAUDE_DOTFILES_SOURCE_ROOT, "
        "or keep a valid clone at ~/claude-dotfiles."
    )


def resolve_home_dir() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        return Path(home).expanduser().resolve()
    return Path.home().resolve()


def write_status(label: str, message: str) -> None:
    print(f"  {label:<5} {message}")


def should_ignore_relative_path(relative_path: Path) -> bool:
    return any(part in IGNORE_NAMES for part in relative_path.parts)


def collect_source_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source_root)
        if should_ignore_relative_path(relative):
            continue
        files.append(relative)
    return sorted(files)


def prune_empty_dirs(root: Path) -> None:
    if not root.is_dir():
        return
    for directory in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def read_json_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, data: dict) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_manifest(path: Path) -> set[Path]:
    data = read_json_file(path)
    entries = data.get("managed", [])
    managed: set[Path] = set()
    if not isinstance(entries, list):
        return managed
    for item in entries:
        if isinstance(item, str) and item:
            managed.add(Path(item))
    return managed


def write_manifest(path: Path, entries: set[Path]) -> None:
    write_json_file(path, {"managed": [entry.as_posix() for entry in sorted(entries)]})


def shell_join(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess_list2cmdline(command)
    return shlex.join(command)


def subprocess_list2cmdline(command: list[str]) -> str:
    import subprocess

    return subprocess.list2cmdline(command)


def build_statusline_command(destination: Path) -> str:
    return shell_join([sys.executable, str(destination)])


def sync_tree(source_root: Path, destination_root: Path, *, force: bool, retired_files: set[Path] | None = None) -> None:
    destination_root.mkdir(parents=True, exist_ok=True)
    source_files = collect_source_files(source_root)
    source_set = set(source_files)
    manifest_path = destination_root / MANIFEST_NAME
    previously_managed = read_manifest(manifest_path)
    managed_entries = {relative for relative in previously_managed if relative in source_set}

    for relative in source_files:
        src = source_root / relative
        dst = destination_root / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if not force:
                write_status("SKIP", relative.as_posix())
                if relative in previously_managed:
                    managed_entries.add(relative)
                continue
            if relative not in previously_managed:
                write_status("KEEP", relative.as_posix())
                continue
        shutil.copy2(src, dst)
        write_status("COPY", relative.as_posix())
        managed_entries.add(relative)

    for relative in sorted(previously_managed - source_set, reverse=True):
        if should_ignore_relative_path(relative):
            continue
        path = destination_root / relative
        if path.is_file():
            path.unlink()
            write_status("PRUNE", relative.as_posix())

    prune_empty_dirs(destination_root)
    write_manifest(manifest_path, managed_entries)


def install_statusline(*, repo_root: Path, claude_dir: Path, force: bool) -> None:
    print("[statusline]")
    source = repo_root / "dotfiles" / "statusline.py"
    destination = claude_dir / "statusline.py"
    claude_dir.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        write_status("SKIP", "statusline.py")
    else:
        shutil.copy2(source, destination)
        write_status("COPY", "statusline.py")

    settings_path = claude_dir / "settings.json"
    settings = read_json_file(settings_path)
    command = build_statusline_command(destination)
    desired = {"type": "command", "command": command}
    if settings.get("statusLine") == desired:
        write_status("SKIP", "statusLine (already configured)")
    else:
        settings["statusLine"] = desired
        write_json_file(settings_path, settings)
        write_status("SET", f"statusLine -> {command}")
    print()


def install_dotfiles(
    *,
    repo_root: Path,
    claude_dir: Path,
    codex_dir: Path,
    force: bool,
    include_codex: bool,
    include_statusline: bool,
) -> None:
    print("=== Claude Code dotfiles setup (Python) ===")
    print(f"Source:  {repo_root}")
    print(f"Target:  {claude_dir}")
    print()
    claude_dir.mkdir(parents=True, exist_ok=True)
    write_source_metadata(claude_dir, repo_root)

    mappings = [
        ("commands", repo_root / "commands", claude_dir / "commands"),
        ("templates", repo_root / "templates", claude_dir / "templates"),
        ("scripts", repo_root / "scripts", claude_dir / "scripts"),
    ]
    for label, source_root, destination_root in mappings:
        print(f"[{label}]")
        sync_tree(
            source_root,
            destination_root,
            force=force,
            retired_files=PRE_MANIFEST_RETIREMENTS.get(label, set()),
        )
        print()

    if include_codex:
        print("[codex-skills]")
        sync_tree(
            repo_root / "codex" / "skills",
            codex_dir / "skills",
            force=force,
            retired_files=PRE_MANIFEST_RETIREMENTS.get("codex-skills", set()),
        )
        print()

        print("[codex-plugin-fixes]")
        try:
            updates = fix_plugin_prompts_if_available()
        except Exception as exc:
            write_status("WARN", f"fix-codex-plugin-prompts.py failed: {exc}")
        else:
            if updates:
                for name in updates:
                    write_status("FIX", name)
            else:
                write_status("SKIP", "fix-codex-plugin-prompts.py (no updates needed)")
        print()

    if include_statusline:
        install_statusline(repo_root=repo_root, claude_dir=claude_dir, force=force)

    print("=== Done ===")
    print()
    print("Available commands:")
    print("  /init-project    Set up a new project with Claude Code × Codex workflow")
    print("  /update-workflow Refresh workflow commands/agents for an existing project")
    print()
    print("Options:")
    print("  -f               Overwrite managed files")
    print("  --codex          Also install Codex global skills into ~/.codex/skills")
    print("  --statusline     Also install the custom Claude Code statusline")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    home = resolve_home_dir()
    claude_dir = Path(args.claude_dir).expanduser().resolve() if args.claude_dir else home / ".claude"
    codex_dir = Path(args.codex_dir).expanduser().resolve() if args.codex_dir else home / ".codex"
    repo_root = resolve_repo_root(args.source_root, claude_dir=claude_dir)

    try:
        install_dotfiles(
            repo_root=repo_root,
            claude_dir=claude_dir,
            codex_dir=codex_dir,
            force=args.force,
            include_codex=args.codex,
            include_statusline=args.statusline,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
