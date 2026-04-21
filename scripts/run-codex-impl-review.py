#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ALLOWED_VERDICTS = ("APPROVED", "CONDITIONAL", "REVISE")
ALLOWED_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")
WINDOWS_SANDBOX_RETRY_PATTERNS = (
    "CreateProcessAsUserW failed",
    "windows sandbox: runner error",
    "windows sandbox failed",
    "Windows sandbox setup is missing or out of date",
    "Couldn't set up your sandbox with Administrator permissions",
)
PLUGIN_PROMPT_MAP = {
    "build-ios-apps": "Design App Intents, build or refactor SwiftUI UI, audit performance, or debug iOS apps in Simulator.",
    "life-science-research": "Route life-science research tasks, synthesize evidence, and use bounded parallel analysis when it materially helps.",
}


@dataclass(frozen=True)
class RunnerPaths:
    repo_root: Path
    agents_dir: Path
    prompt_path: Path
    context_dir: Path
    reviews_dir: Path
    sessions_path: Path
    bundle_path: Path
    context_output_path: Path
    review_output_path: Path

    @classmethod
    def from_repo_root(
        cls,
        repo_root: Path,
        prompt_path_override: str | None,
        agents_root_override: str | None,
    ) -> "RunnerPaths":
        agents_dir = (
            resolve_optional_path(agents_root_override, repo_root)
            if agents_root_override
            else repo_root / ".agents"
        )
        context_dir = agents_dir / "context"
        reviews_dir = agents_dir / "reviews"
        prompt_path = (
            resolve_optional_path(prompt_path_override, repo_root)
            if prompt_path_override
            else agents_dir / "prompts" / "codex_impl_review.md"
        )
        return cls(
            repo_root=repo_root,
            agents_dir=agents_dir,
            prompt_path=prompt_path,
            context_dir=context_dir,
            reviews_dir=reviews_dir,
            sessions_path=reviews_dir / "sessions.json",
            bundle_path=context_dir / "_codex_input.tmp",
            context_output_path=context_dir / "codex_impl_review.md",
            review_output_path=reviews_dir / "impl-review.md",
        )


@dataclass(frozen=True)
class ReviewAttemptResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an implementation review bundle and optionally run `codex review -` without requiring pwsh."
    )
    parser.add_argument("--task-description", default="")
    parser.add_argument("--files", nargs="*", default=[])
    parser.add_argument("--include-files", nargs="*", default=[])
    parser.add_argument("--review-timeout-sec", type=int, default=600)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--reasoning-effort", choices=ALLOWED_REASONING_EFFORTS, default="high")
    parser.add_argument("--no-previous", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dump-bundle")
    parser.add_argument("--write-trace")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--prompt-path")
    parser.add_argument("--agents-root", help="Optional override for the workflow root. Defaults to .agents.")
    parser.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    return parser.parse_args(argv)


def resolve_optional_path(path_value: str, repo_root: Path) -> Path:
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def debug_log(enabled: bool, message: str) -> None:
    if enabled:
        print(message, file=sys.stderr)


def read_text_strict(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_bundle_text(path: Path, content: str, repo_root: Path) -> Path:
    try:
        write_text(path, content)
        return path
    except PermissionError:
        fallback_dir = repo_root / "tmp" / "impl-review-bundles"
        fallback_path = fallback_dir / f"{path.stem}.{os.getpid()}{path.suffix}"
        write_text(fallback_path, content)
        return fallback_path


def append_section(parts: list[str], title: str, content: str | None) -> None:
    if content is None:
        return
    text = str(content).strip()
    if not text:
        return
    parts.extend(["---", f"# {title}", "", text, ""])


def normalize_repo_paths(input_paths: Sequence[str], repo_root: Path) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()
    repo_root_abs = repo_root.resolve()
    for item in input_paths:
        if not item:
            continue
        candidate = Path(item).expanduser()
        if not candidate.is_absolute():
            candidate = repo_root_abs / candidate
        candidate_abs = candidate.resolve()
        try:
            relative = candidate_abs.relative_to(repo_root_abs)
        except ValueError as exc:
            raise ValueError(f"Path is outside repo root: {item}") from exc
        normalized = relative.as_posix()
        if normalized not in seen:
            seen.add(normalized)
            resolved.append(normalized)
    return resolved


def run_command(
    args: Sequence[str],
    repo_root: Path,
    *,
    input_text: str | None = None,
    timeout_sec: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=repo_root,
        input=input_text,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout_sec,
        check=False,
    )


def command_output_nul_entries(result: subprocess.CompletedProcess[str]) -> list[str]:
    text = result.stdout or ""
    if "\0" in text:
        return [entry for entry in text.split("\0") if entry]
    return [line.strip() for line in text.splitlines() if line.strip()]


def get_changed_files(repo_root: Path) -> list[str]:
    commands = [
        ["git", "diff", "--name-only", "-z", "--diff-filter=ACDMRTUXB"],
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACDMRTUXB"],
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    ]
    combined: list[str] = []
    seen: set[str] = set()
    for command in commands:
        result = run_command(command, repo_root)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip() or f"{' '.join(command)} failed."
            raise RuntimeError(f"Unable to determine changed files from git. Pass --files explicitly.\n{detail}")
        for line in command_output_nul_entries(result):
            if line not in seen:
                seen.add(line)
                combined.append(line)
    return combined


def resolve_codex_executable(codex_bin: str) -> str:
    candidate = os.path.expanduser(codex_bin)
    resolved = shutil.which(candidate)
    if resolved:
        resolved_path = Path(resolved)
        if resolved_path.suffix.lower() == ".ps1":
            raise RuntimeError(
                "Resolved codex command points to a PowerShell script wrapper that the Python runner cannot launch directly. "
                "Use a runnable codex executable on PATH, or pass `--codex-bin` / `CODEX_BIN` to an executable path instead of a `.ps1` shim."
            )
        return resolved
    raise RuntimeError(
        "Unable to locate a runnable codex executable. Ensure `codex` is on PATH or pass `--codex-bin` / set `CODEX_BIN` "
        "to an executable path. PowerShell alias/function wrappers are not supported by the Python runner."
    )


def should_retry_unelevated(stderr_text: str, stdout_text: str) -> bool:
    combined = "\n".join(part for part in (stderr_text, stdout_text) if part).lower()
    return any(pattern.lower() in combined for pattern in WINDOWS_SANDBOX_RETRY_PATTERNS)


def build_codex_review_args(*, codex_exec: str, model: str, reasoning_effort: str, unelevated: bool) -> list[str]:
    args = [
        codex_exec,
        "review",
        "-c",
        f'model="{model}"',
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
    ]
    if unelevated:
        args.extend(["-c", 'windows.sandbox="unelevated"'])
    args.append("-")
    return args


def run_codex_review_attempt(
    *,
    codex_exec: str,
    bundle_text: str,
    repo_root: Path,
    timeout_sec: int,
    model: str,
    reasoning_effort: str,
    unelevated: bool,
) -> ReviewAttemptResult:
    try:
        result = run_command(
            build_codex_review_args(
                codex_exec=codex_exec,
                model=model,
                reasoning_effort=reasoning_effort,
                unelevated=unelevated,
            ),
            repo_root,
            input_text=bundle_text,
            timeout_sec=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return ReviewAttemptResult(returncode=-1, stdout=stdout, stderr=stderr, timed_out=True)

    return ReviewAttemptResult(
        returncode=result.returncode,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        timed_out=False,
    )


def get_result_detail(result: ReviewAttemptResult, codex_exec: str, timeout_sec: int) -> str:
    stderr = result.stderr.strip()
    stdout = result.stdout.strip()
    if result.timed_out:
        return stderr or stdout or f"`{codex_exec} review -` timed out after {timeout_sec} seconds."
    return stderr or stdout or f"`{codex_exec} review -` exited with code {result.returncode}."


def is_windows_host() -> bool:
    return os.name == "nt"


def prefer_unelevated_retry() -> bool:
    return os.environ.get("CODEX_REVIEW_FORCE_UNELEVATED", "").strip().lower() in {"1", "true", "yes"}


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
            data = json.loads(read_text_strict(manifest_path))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        interface = data.setdefault("interface", {})
        if str(interface.get("defaultPrompt", "")) == prompt:
            continue
        interface["defaultPrompt"] = prompt
        write_text(manifest_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        updates.append(plugin_name)
    return updates


def get_untracked_target_files(repo_root: Path, target_files: Sequence[str]) -> list[str]:
    if not target_files:
        return []
    result = run_command(
        ["git", "status", "--porcelain", "-z", "--untracked-files=all", "--", *target_files],
        repo_root,
    )
    if result.returncode != 0:
        return []
    untracked: list[str] = []
    for entry in command_output_nul_entries(result):
        if entry.startswith("?? "):
            path = entry[3:]
            if path:
                untracked.append(path)
    return untracked


def get_no_index_diff(repo_root: Path, relative_path: str) -> str:
    result = run_command(["git", "diff", "--no-index", "--", os.devnull, relative_path], repo_root)
    if result.returncode not in (0, 1):
        detail = (result.stderr or result.stdout).strip() or f"git diff --no-index failed for {relative_path}."
        return f"[untracked diff unavailable for {relative_path}: {detail}]"
    return (result.stdout or "").strip()


def get_git_diff(repo_root: Path, target_files: Sequence[str]) -> str:
    if not target_files:
        return ""
    sections: list[str] = []

    working_tree = run_command(["git", "diff", "--no-ext-diff", "--", *target_files], repo_root)
    if working_tree.returncode != 0:
        detail = (working_tree.stderr or working_tree.stdout).strip() or "git diff failed."
        return f"[git diff unavailable: {detail}]"
    working_output = working_tree.stdout.strip()
    if working_output:
        sections.append("## Working tree diff\n" + working_output)

    staged = run_command(["git", "diff", "--cached", "--no-ext-diff", "--", *target_files], repo_root)
    if staged.returncode != 0:
        detail = (staged.stderr or staged.stdout).strip() or "git diff --cached failed."
        return f"[git diff unavailable: {detail}]"
    staged_output = staged.stdout.strip()
    if staged_output:
        sections.append("## Index diff\n" + staged_output)

    for relative_path in get_untracked_target_files(repo_root, target_files):
        untracked_output = get_no_index_diff(repo_root, relative_path)
        if untracked_output:
            sections.append(f"## Untracked diff: {relative_path}\n{untracked_output}")

    if not sections:
        return "[git diff returned no output for the selected files]"
    return "\n\n".join(sections)


def safe_read_project_file(path: Path) -> str:
    try:
        return read_text_strict(path)
    except UnicodeDecodeError:
        return "[binary or non-UTF8 file omitted]"


def get_head_tail_excerpt(
    text: str,
    *,
    max_lines: int = 160,
    head_lines: int = 70,
    tail_lines: int = 24,
    include_line_numbers: bool = False,
) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        if not include_line_numbers:
            return text.rstrip()
        return "\n".join(f"{index + 1:4}: {line}" for index, line in enumerate(lines)).rstrip()

    head_slice = lines[: min(head_lines, len(lines))]
    tail_slice = lines[max(len(lines) - tail_lines, len(head_slice)) :]
    omitted = len(lines) - len(head_slice) - len(tail_slice)
    result_lines: list[str] = []
    if include_line_numbers:
        result_lines.extend(f"{index + 1:4}: {line}" for index, line in enumerate(head_slice))
        if omitted > 0:
            result_lines.append(f"[... omitted {omitted} lines ...]")
        start_index = len(lines) - len(tail_slice)
        result_lines.extend(f"{start_index + index + 1:4}: {line}" for index, line in enumerate(tail_slice))
        return "\n".join(result_lines).rstrip()

    result_lines.extend(head_slice)
    if omitted > 0:
        result_lines.append(f"[... omitted {omitted} lines ...]")
    result_lines.extend(tail_slice)
    return "\n".join(result_lines).rstrip()


def load_prompt_text(prompt_path: Path, substitutions: dict[str, str]) -> str:
    prompt_text = read_text_strict(prompt_path)
    for placeholder, value in substitutions.items():
        prompt_text = prompt_text.replace(placeholder, value)
    return prompt_text


def ensure_sessions_shape(raw_state: dict[str, Any] | None) -> dict[str, Any]:
    state: dict[str, Any] = raw_state or {}
    current = state.setdefault("current", {})
    if not isinstance(current, dict):
        current = {}
        state["current"] = current

    plan_review = current.setdefault("plan_review", {})
    if not isinstance(plan_review, dict):
        plan_review = {}
        current["plan_review"] = plan_review
    plan_review.setdefault("phase_a_cycles", 0)
    plan_review.setdefault("phase_b_cycles", 0)

    impl_review = current.setdefault("impl_review", {})
    if not isinstance(impl_review, dict):
        impl_review = {}
        current["impl_review"] = impl_review
    legacy_cycle = int(impl_review.get("cycle", 0) or 0)
    impl_review.setdefault("alignment_cycle", 0)
    impl_review.setdefault("verification_cycle", 0)
    impl_review.setdefault("quality_cycle", legacy_cycle)
    impl_review.setdefault("macro_cycle", 0)
    impl_review["cycle"] = int(impl_review.get("cycle", legacy_cycle) or 0)

    reviews = state.setdefault("reviews", [])
    if not isinstance(reviews, list):
        state["reviews"] = []
    return state


def read_sessions_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return ensure_sessions_shape({})
    data = json.loads(read_text_strict(path))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid sessions.json content at {path}")
    return ensure_sessions_shape(data)


def write_sessions_state(path: Path, state: dict[str, Any]) -> None:
    write_text(path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def get_impl_cycle(state: dict[str, Any]) -> int:
    return int(state["current"]["impl_review"].get("cycle", 0) or 0)


def set_impl_cycle(state: dict[str, Any], value: int) -> None:
    impl_review = state["current"]["impl_review"]
    impl_review["cycle"] = value
    impl_review["quality_cycle"] = value


def determine_verdict(review_text: str) -> str | None:
    for line in reversed(review_text.splitlines()):
        trimmed = line.strip()
        if not trimmed:
            continue
        for verdict in ALLOWED_VERDICTS:
            if trimmed == f"VERDICT: {verdict}":
                return verdict
        return None
    return None


def compute_bundle_hash(bundle_text: str) -> str:
    return hashlib.sha256(bundle_text.encode("utf-8")).hexdigest()


def get_previous_review_context(review_text: str, fallback_tail_lines: int = 80) -> str:
    if not review_text.strip():
        return ""
    captured_sections: list[str] = []
    for title in ("### Findings", "### Open Questions", "### Residual Risks"):
        start = review_text.find(title)
        if start < 0:
            continue
        next_positions = [
            pos
            for pos in (
                review_text.find("\n### ", start + len(title)),
                review_text.find("\r\n### ", start + len(title)),
            )
            if pos >= 0
        ]
        end = min(next_positions) if next_positions else len(review_text)
        section_text = review_text[start:end].strip()
        if section_text:
            captured_sections.append(section_text)

    verdict_lines = [line.strip() for line in review_text.splitlines() if line.strip().startswith("VERDICT: ")]
    if verdict_lines:
        verdict_line = verdict_lines[-1]
        if captured_sections:
            return "\n\n".join([*captured_sections, verdict_line]).rstrip()
        return verdict_line
    if captured_sections:
        return "\n\n".join(captured_sections).rstrip()
    return "\n".join(review_text.splitlines()[-fallback_tail_lines:]).rstrip()


def build_bundle(
    args: argparse.Namespace,
    paths: RunnerPaths,
) -> tuple[str, list[str], list[str], bool, str]:
    target_files = (
        normalize_repo_paths(args.files, paths.repo_root)
        if args.files
        else normalize_repo_paths(get_changed_files(paths.repo_root), paths.repo_root)
    )
    if not target_files:
        raise RuntimeError("No files to review.")

    dependency_files = normalize_repo_paths(args.include_files, paths.repo_root)
    task_summary = args.task_description.strip() or f"Review changes in {', '.join(target_files)}"
    prompt_text = load_prompt_text(
        paths.prompt_path,
        {"$TASK_DESCRIPTION": task_summary, "$FILE_LIST": ", ".join(target_files)},
    )

    sections: list[str] = []
    append_section(
        sections,
        "Review Runner Config",
        (
            f"model = {args.model}\n"
            f"reasoning_effort = {args.reasoning_effort}\n"
            f"timeout_seconds = {args.review_timeout_sec}"
        ),
    )
    append_section(sections, "Prompt", prompt_text)
    append_section(sections, "git diff", get_git_diff(paths.repo_root, target_files))

    for relative_path in target_files:
        full_path = paths.repo_root / Path(relative_path)
        if full_path.is_file():
            append_section(
                sections,
                f"file: {relative_path}",
                get_head_tail_excerpt(
                    safe_read_project_file(full_path),
                    max_lines=220,
                    head_lines=120,
                    tail_lines=36,
                    include_line_numbers=True,
                ),
            )

    for relative_path in dependency_files:
        full_path = paths.repo_root / Path(relative_path)
        if full_path.is_file():
            append_section(
                sections,
                f"dependency: {relative_path}",
                get_head_tail_excerpt(
                    safe_read_project_file(full_path),
                    max_lines=180,
                    head_lines=80,
                    tail_lines=24,
                    include_line_numbers=True,
                ),
            )

    previous_review_used = False
    if not args.no_previous and paths.context_output_path.is_file():
        previous_review_text = get_previous_review_context(read_text_strict(paths.context_output_path))
        append_section(sections, "Previous Review", previous_review_text)
        previous_review_used = bool(previous_review_text)

    return "\n".join(sections).rstrip() + "\n", target_files, dependency_files, previous_review_used, task_summary


def invoke_codex_review(
    *,
    codex_exec: str,
    bundle_text: str,
    repo_root: Path,
    timeout_sec: int,
    model: str,
    reasoning_effort: str,
) -> tuple[str, str]:
    fix_plugin_prompts_if_available()

    attempts: list[tuple[str, bool]] = []
    if is_windows_host() and prefer_unelevated_retry():
        attempts.append(("unelevated", True))
    attempts.append(("default", False))
    if is_windows_host() and not prefer_unelevated_retry():
        attempts.append(("unelevated", True))

    last_error: str | None = None
    last_stderr = ""
    for label, unelevated in attempts:
        result = run_codex_review_attempt(
            codex_exec=codex_exec,
            bundle_text=bundle_text,
            repo_root=repo_root,
            timeout_sec=timeout_sec,
            model=model,
            reasoning_effort=reasoning_effort,
            unelevated=unelevated,
        )
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        if result.returncode == 0:
            if not stdout:
                raise RuntimeError("`codex review -` returned empty output.")
            if label == "unelevated" and not prefer_unelevated_retry():
                note = 'Codex elevated Windows sandbox failed; retried with windows.sandbox="unelevated".'
                stderr = f"{stderr}\n{note}".strip() if stderr else note
            return stdout, stderr

        detail = get_result_detail(result, codex_exec, timeout_sec)
        last_error = detail
        last_stderr = stderr
        if label == "default" and is_windows_host() and should_retry_unelevated(stderr, stdout):
            continue
        break

    if last_stderr:
        raise RuntimeError(last_stderr if last_stderr.strip() else last_error or "codex review failed.")
    raise RuntimeError(last_error or "codex review failed.")


def build_trace_payload(
    args: argparse.Namespace,
    paths: RunnerPaths,
    *,
    bundle_path: Path,
    current_cycle: int,
    task_summary: str,
    target_files: Sequence[str],
    dependency_files: Sequence[str],
    previous_review_used: bool,
    bundle_text: str,
    status: str,
    verdict: str | None = None,
    error: str | None = None,
    stderr_text: str | None = None,
    resolved_codex_bin: str | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": status,
        "current_cycle": current_cycle,
        "task_description": task_summary,
        "target_files": list(target_files),
        "dependency_files": list(dependency_files),
        "previous_review_used": previous_review_used,
        "prompt_path": str(paths.prompt_path),
        "bundle_path": str(bundle_path),
        "context_output_path": str(paths.context_output_path),
        "review_output_path": str(paths.review_output_path),
        "sessions_path": str(paths.sessions_path),
        "bundle_sha256": compute_bundle_hash(bundle_text),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "review_timeout_sec": args.review_timeout_sec,
        "verdict": verdict,
        "error": error,
        "stderr": stderr_text,
        "codex_bin": args.codex_bin,
        "resolved_codex_bin": resolved_codex_bin,
        "dry_run": args.dry_run,
    }


def write_trace(trace_path: str | None, payload: dict[str, Any]) -> None:
    if trace_path:
        write_text(Path(trace_path), json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path.cwd().resolve()
    paths = RunnerPaths.from_repo_root(repo_root, args.prompt_path, args.agents_root)

    bundle_text = ""
    target_files: list[str] = []
    dependency_files: list[str] = []
    previous_review_used = False
    task_summary = ""
    resolved_codex_bin: str | None = None
    bundle_path = paths.bundle_path
    current_cycle = 0
    sessions_state: dict[str, Any] | None = None

    try:
        sessions_state = read_sessions_state(paths.sessions_path)
        current_cycle = get_impl_cycle(sessions_state) + 1
        bundle_text, target_files, dependency_files, previous_review_used, task_summary = build_bundle(args, paths)
        bundle_path = write_bundle_text(paths.bundle_path, bundle_text, paths.repo_root)
        if args.dump_bundle:
            write_text(Path(args.dump_bundle), bundle_text)

        debug_log(args.debug, f"model={args.model} reasoning_effort={args.reasoning_effort}")
        debug_log(args.debug, f"target_files={','.join(target_files)}")
        debug_log(args.debug, f"bundle_path={bundle_path}")

        if args.dry_run:
            write_trace(
                args.write_trace,
                build_trace_payload(
                    args,
                    paths,
                    bundle_path=bundle_path,
                    current_cycle=current_cycle,
                    task_summary=task_summary,
                    target_files=target_files,
                    dependency_files=dependency_files,
                    previous_review_used=previous_review_used,
                    bundle_text=bundle_text,
                    status="dry-run",
                ),
            )
            print("Status: dry-run")
            print(f"Model: {args.model}")
            print(f"ReasoningEffort: {args.reasoning_effort}")
            print(f"Bundle: {bundle_path}")
            return 0

        resolved_codex_bin = resolve_codex_executable(args.codex_bin)

        review_text, stderr_text = invoke_codex_review(
            codex_exec=resolved_codex_bin,
            bundle_text=bundle_text,
            repo_root=paths.repo_root,
            timeout_sec=args.review_timeout_sec,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
        verdict = determine_verdict(review_text)
        if verdict is None:
            review_text = review_text.rstrip() + "\n\nVERDICT: CONDITIONAL\n"
            verdict = "CONDITIONAL"
        else:
            review_text = review_text.rstrip() + "\n"

        set_impl_cycle(sessions_state, current_cycle)
        write_text(paths.context_output_path, review_text)
        write_text(paths.review_output_path, review_text)
        if verdict == "APPROVED":
            set_impl_cycle(sessions_state, 0)
            sessions_state.setdefault("reviews", []).append(
                {
                    "kind": "impl-review",
                    "cycle": current_cycle,
                    "date": datetime.now(timezone.utc).astimezone().isoformat(),
                    "verdict": verdict,
                }
            )
        write_sessions_state(paths.sessions_path, sessions_state)

        write_trace(
            args.write_trace,
            build_trace_payload(
                    args,
                    paths,
                    bundle_path=bundle_path,
                    current_cycle=current_cycle,
                task_summary=task_summary,
                target_files=target_files,
                dependency_files=dependency_files,
                previous_review_used=previous_review_used,
                bundle_text=bundle_text,
                status="ok",
                verdict=verdict,
                stderr_text=stderr_text,
                resolved_codex_bin=resolved_codex_bin,
            ),
        )
        print(f"VERDICT: {verdict}")
        print(f"Cycle: {current_cycle}")
        print(f"Model: {args.model}")
        print(f"ReasoningEffort: {args.reasoning_effort}")
        print(f"Bundle: {bundle_path}")
        print(f"Review: {paths.context_output_path}")
        print(f"Sessions: {paths.sessions_path}")
        return 0
    except Exception as exc:
        write_trace(
            args.write_trace,
            build_trace_payload(
                args,
                paths,
                bundle_path=bundle_path,
                current_cycle=current_cycle,
                task_summary=task_summary,
                target_files=target_files,
                dependency_files=dependency_files,
                previous_review_used=previous_review_used,
                bundle_text=bundle_text,
                status="failed",
                error=str(exc),
                resolved_codex_bin=resolved_codex_bin,
            ),
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
