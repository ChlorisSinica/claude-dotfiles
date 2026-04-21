#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import locale
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class VerifyConfig:
    command: str
    shell: str
    log_dir: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repo verify command from scripts/verify-config.json and write status/log artifacts."
    )
    parser.add_argument("--config", default="scripts/verify-config.json")
    parser.add_argument("--command")
    parser.add_argument("--shell")
    parser.add_argument("--log-dir")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv)


def debug_log(enabled: bool, message: str) -> None:
    if enabled:
        print(message, file=sys.stderr)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_verify_config(config_path: Path) -> VerifyConfig:
    if config_path.is_file():
        data = json.loads(read_text(config_path))
        if not isinstance(data, dict):
            raise ValueError(f"Invalid verify config at {config_path}")
        command = str(data.get("VERIFY_CMD", "")).strip()
        shell = str(data.get("VERIFY_SHELL", "")).strip() or "direct"
        log_dir = str(data.get("PRIMARY_LOG_DIR", "")).strip() or ".agents/logs/verify"
        if not command:
            raise ValueError(f"VERIFY_CMD is missing in {config_path}")
        return VerifyConfig(command=command, shell=shell, log_dir=log_dir)
    return VerifyConfig(
        command="python -m pytest --tb=short -q",
        shell="direct",
        log_dir=".agents/logs/verify",
    )


def resolve_shell_command(shell_name: str) -> tuple[list[str], str | None]:
    normalized = shell_name.strip().lower()
    if normalized in {"", "direct"}:
        return [], None
    if normalized == "bash":
        bash_exec = shutil.which("bash")
        if bash_exec:
            return [bash_exec, "-lc"], None
        raise RuntimeError("VERIFY_SHELL=bash but bash was not found.")
    if normalized == "powershell":
        pwsh_exec = shutil.which("pwsh")
        if pwsh_exec:
            return [pwsh_exec, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"], "utf-8"
        powershell_exec = shutil.which("powershell")
        if powershell_exec:
            return [powershell_exec, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"], None
        raise RuntimeError("VERIFY_SHELL=powershell but PowerShell was not found.")
    raise RuntimeError(f"Unsupported VERIFY_SHELL: {shell_name}")


def normalize_powershell_command(command: str) -> str:
    stripped = command.lstrip()
    if not stripped:
        return command
    if stripped.startswith("&"):
        return command
    if stripped[0] in {'"', "'"}:
        return f"& {command}"
    return command


def build_subprocess_args(config: VerifyConfig) -> tuple[list[str], bool, str | None]:
    shell_cmd, decode_encoding = resolve_shell_command(config.shell)
    if not shell_cmd:
        return shlex.split(config.command, posix=os.name != "nt"), False, decode_encoding
    command = config.command
    if config.shell.strip().lower() == "powershell":
        command = normalize_powershell_command(command)
    return [*shell_cmd, command], False, decode_encoding


def decode_stream(data: bytes | str | None, *, encoding_hint: str | None = None) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    preferred = encoding_hint or locale.getpreferredencoding(False) or "utf-8"
    return data.decode(preferred, errors="replace")


def write_console_text(text: str) -> None:
    encoding = sys.stdout.encoding or locale.getpreferredencoding(False) or "utf-8"
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(text.encode(encoding, errors="replace"))
        return
    sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def run_verify_command(config: VerifyConfig, repo_root: Path) -> tuple[int, str]:
    args, use_shell, decode_encoding = build_subprocess_args(config)
    result = subprocess.run(
        args,
        cwd=repo_root,
        capture_output=True,
        text=False,
        shell=use_shell,
        check=False,
    )
    output = ""
    stdout_text = decode_stream(result.stdout, encoding_hint=decode_encoding)
    stderr_text = decode_stream(result.stderr, encoding_hint=decode_encoding)
    if stdout_text:
        output += stdout_text
    if stderr_text:
        output += stderr_text
    return int(result.returncode), output


def write_verify_artifacts(
    *,
    repo_root: Path,
    config: VerifyConfig,
    output_text: str,
    exit_code: int,
) -> tuple[Path, Path]:
    log_dir = repo_root / config.log_dir
    history_dir = log_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc).astimezone()
    timestamp = started.strftime("%Y%m%d-%H%M%S-%f")
    started_at = started.isoformat()
    log_path = history_dir / f"{timestamp}-verify.log"
    status_path = history_dir / f"{timestamp}-status.json"
    latest_log = log_dir / "latest.log"
    latest_status = log_dir / "latest.status.json"

    write_text(log_path, output_text.rstrip() + ("\n" if output_text else ""))
    finished_at = datetime.now(timezone.utc).astimezone().isoformat()
    status = {
        "ok": exit_code == 0,
        "command": config.command,
        "shell": config.shell,
        "exit_code": exit_code,
        "started_at": started_at,
        "finished_at": finished_at,
        "log_path": str(log_path),
    }
    write_text(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    write_text(latest_log, read_text(log_path))
    write_text(latest_status, read_text(status_path))
    return log_path, status_path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path.cwd().resolve()
    config = load_verify_config((repo_root / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config))
    if args.command:
        config = VerifyConfig(command=args.command, shell=config.shell, log_dir=config.log_dir)
    if args.shell:
        config = VerifyConfig(command=config.command, shell=args.shell, log_dir=config.log_dir)
    if args.log_dir:
        config = VerifyConfig(command=config.command, shell=config.shell, log_dir=args.log_dir)

    debug_log(args.debug, f"command={config.command}")
    debug_log(args.debug, f"shell={config.shell}")

    try:
        exit_code, output_text = run_verify_command(config, repo_root)
    except Exception as exc:
        exit_code = 1
        output_text = f"ERROR: {exc}\n"

    if output_text:
        write_console_text(output_text)
        if not output_text.endswith("\n"):
            write_console_text("\n")
    log_path, status_path = write_verify_artifacts(
        repo_root=repo_root,
        config=config,
        output_text=output_text,
        exit_code=exit_code,
    )
    print(f"ExitCode: {exit_code}")
    print(f"Log: {log_path}")
    print(f"Status: {status_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
