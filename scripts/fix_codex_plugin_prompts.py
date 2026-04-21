#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PLUGIN_PROMPT_MAP = {
    "build-ios-apps": "Design App Intents, build or refactor SwiftUI UI, audit performance, or debug iOS apps in Simulator.",
    "life-science-research": "Route life-science research tasks, synthesize evidence, and use bounded parallel analysis when it materially helps.",
}


def is_windows_host() -> bool:
    return os.name == "nt"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def default_plugins_root() -> Path:
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path.home())
    return Path(home).expanduser() / ".codex" / ".tmp" / "plugins" / "plugins"


def fix_plugin_prompts_if_available(plugins_root: Path | None = None) -> list[str]:
    if not is_windows_host():
        return []
    root = plugins_root or default_plugins_root()
    if not root.is_dir():
        return []

    updates: list[str] = []
    for plugin_name, prompt in PLUGIN_PROMPT_MAP.items():
        manifest_path = root / plugin_name / ".codex-plugin" / "plugin.json"
        if not manifest_path.is_file():
            continue
        if len(prompt) > 128:
            raise RuntimeError(f"defaultPrompt for {plugin_name} exceeds 128 characters.")
        try:
            data = json.loads(read_text(manifest_path))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        interface = data.setdefault("interface", {})
        if str(interface.get("defaultPrompt", "")) == prompt:
            continue
        interface["defaultPrompt"] = prompt
        write_text(manifest_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        updates.append(plugin_name)
    return updates


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Best-effort fix for known Codex plugin defaultPrompt warnings.")
    parser.add_argument("--plugins-root")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plugins_root = Path(args.plugins_root).expanduser() if args.plugins_root else None
    try:
        updates = fix_plugin_prompts_if_available(plugins_root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if updates:
        print("Updated plugin prompts:")
        for name in updates:
            print(f"- {name}")
    else:
        print("No plugin prompt updates were needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
