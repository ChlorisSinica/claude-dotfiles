@python -X utf8 -x "%~f0" %* & @exit /b
"""Claude Code session manager.

Usage:
    clear-sessions.bat --list [project-path]
    clear-sessions.bat --delete ID [project-path]
    clear-sessions.bat --delete-all [project-path]
    clear-sessions.bat [project-path]          (same as --delete-all)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def resolve_session_dir(project_path: str) -> Path:
    project = Path(project_path).resolve()
    if not project.is_dir():
        print(f"[ERROR] Directory not found: {project}", file=sys.stderr)
        sys.exit(1)
    dir_name = str(project).replace(":\\", "--").replace("\\", "-").replace("/", "-")
    session_dir = Path.home() / ".claude" / "projects" / dir_name
    if not session_dir.is_dir():
        print(f"[ERROR] Session directory not found: {session_dir}",
              file=sys.stderr)
        sys.exit(1)
    return session_dir


def _clean_title(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).strip()
    first = text.split("\n")[0].strip()
    return first[:120] + "..." if len(first) > 120 else first


def parse_session(filepath: Path) -> dict:
    stat = filepath.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    first_ts, title, count = None, None, 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            count += 1
            if first_ts is None and "timestamp" in obj:
                first_ts = obj["timestamp"]
            if title is None and obj.get("type") == "user":
                msg = obj.get("message", {})
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content", "")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        i.get("text", "")[:200]
                        for i in content if isinstance(i, dict)
                    )
                else:
                    text = str(content)
                cleaned = _clean_title(text)
                if cleaned:
                    title = cleaned
    return {
        "id": filepath.stem,
        "title": title or "(no user message)",
        "created": first_ts or mtime,
        "modified": mtime,
        "size_bytes": stat.st_size,
        "messages": count,
    }


def cmd_list(session_dir: Path) -> None:
    sessions = [
        parse_session(f)
        for f in sorted(session_dir.glob("*.jsonl"), key=os.path.getmtime)
    ]
    sys.stdout.buffer.write(
        json.dumps(sessions, ensure_ascii=False, indent=2).encode("utf-8")
        + b"\n"
    )


def cmd_delete(session_dir: Path, session_id: str) -> None:
    target = session_dir / f"{session_id}.jsonl"
    if not target.exists():
        matches = list(session_dir.glob(f"{session_id}*.jsonl"))
        if len(matches) == 1:
            target = matches[0]
        elif len(matches) > 1:
            print("[ERROR] Ambiguous ID. Matches:", file=sys.stderr)
            for m in matches:
                print(f"  {m.stem}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"[ERROR] Session not found: {session_id}", file=sys.stderr)
            sys.exit(1)
    target.unlink()
    print(f"Deleted: {target.stem}")


def cmd_delete_all(session_dir: Path) -> None:
    count = 0
    for f in session_dir.glob("*.jsonl"):
        f.unlink()
        count += 1
    print(f"Deleted {count} session file(s) from {session_dir}")


def main() -> None:
    # Default project: parent of .claude/ dir (where this script lives)
    script_dir = Path(sys.argv[0]).resolve().parent
    default_project = str(script_dir.parent)

    parser = argparse.ArgumentParser(description="Claude Code session manager")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true",
                       help="List sessions as JSON")
    group.add_argument("--delete", metavar="ID",
                       help="Delete session by ID (prefix match)")
    group.add_argument("--delete-all", action="store_true",
                       help="Delete all sessions (default)")
    parser.add_argument("project", nargs="?", default=default_project,
                        help="Project root path")
    args = parser.parse_args()

    session_dir = resolve_session_dir(args.project)

    if args.list:
        cmd_list(session_dir)
    elif args.delete:
        cmd_delete(session_dir, args.delete)
    else:
        cmd_delete_all(session_dir)


if __name__ == "__main__":
    main()
