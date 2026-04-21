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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fix_codex_plugin_prompts import fix_plugin_prompts_if_available


ALLOWED_CYCLE_TYPES = ("alignment", "verification", "quality")
ALLOWED_REVIEW_UNITS = ("task", "milestone", "batch")
ALLOWED_VERDICTS = ("APPROVED", "CONDITIONAL", "REVISE")
ALLOWED_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")
WINDOWS_SANDBOX_RETRY_PATTERNS = (
    "CreateProcessAsUserW failed",
    "windows sandbox: runner error",
    "windows sandbox failed",
    "Windows sandbox setup is missing or out of date",
    "Couldn't set up your sandbox with Administrator permissions",
)


@dataclass(frozen=True)
class RunnerPaths:
    repo_root: Path
    prompt_root: Path
    context_dir: Path
    reviews_dir: Path
    sessions_path: Path
    bundle_path: Path
    phase_output_path: Path
    latest_context_output_path: Path
    latest_review_output_path: Path

    @classmethod
    def from_repo_root(
        cls,
        repo_root: Path,
        cycle_type: str,
        prompt_root_override: str | None,
        agents_root_override: str | None,
    ) -> "RunnerPaths":
        agents_dir = (
            resolve_optional_path(agents_root_override, repo_root)
            if agents_root_override
            else repo_root / ".agents"
        )
        context_dir = agents_dir / "context"
        reviews_dir = agents_dir / "reviews"
        prompt_root = (
            resolve_optional_path(prompt_root_override, repo_root)
            if prompt_root_override
            else agents_dir / "prompts" / "impl-review"
        )
        return cls(
            repo_root=repo_root,
            prompt_root=prompt_root,
            context_dir=context_dir,
            reviews_dir=reviews_dir,
            sessions_path=reviews_dir / "sessions.json",
            bundle_path=context_dir / "_codex_input.tmp",
            phase_output_path=context_dir / f"codex_impl_review.{cycle_type}.md",
            latest_context_output_path=context_dir / "codex_impl_review.md",
            latest_review_output_path=reviews_dir / "impl-review.md",
        )


@dataclass(frozen=True)
class ReviewAttemptResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a phase-aware implementation review bundle and optionally run "
            "`codex review -` without requiring pwsh."
        )
    )
    parser.add_argument("--cycle-type", choices=ALLOWED_CYCLE_TYPES, default="quality")
    parser.add_argument("--review-unit", choices=ALLOWED_REVIEW_UNITS, default="task")
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
    parser.add_argument("--prompt-root")
    parser.add_argument(
        "--agents-root",
        help="Optional override for the workflow root. Defaults to .agents.",
    )
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
        fallback_dir = repo_root / "tmp" / "impl-cycle-bundles"
        fallback_path = fallback_dir / f"{path.stem}.{os.getpid()}{path.suffix}"
        write_text(fallback_path, content)
        return fallback_path


def append_section(parts: list[str], title: str, content: str | None) -> None:
    if content is None:
        return
    text = str(content).strip()
    if not text:
        return
    parts.append("---")
    parts.append(f"# {title}")
    parts.append("")
    parts.append(text)
    parts.append("")


def normalize_repo_paths(input_paths: Sequence[str], repo_root: Path) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()
    repo_root = repo_root.resolve()
    for item in input_paths:
        if not item:
            continue
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        candidate = candidate.resolve()
        try:
            relative = candidate.relative_to(repo_root)
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


def command_output_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    text = result.stdout or ""
    return [line.strip() for line in text.splitlines() if line.strip()]


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
            raise RuntimeError(
                f"Unable to determine changed files from git. Pass --files explicitly.\n{detail}"
            )
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
                "Resolved codex command points to a PowerShell script wrapper that the Python "
                "runner cannot launch directly. Use a runnable codex executable on PATH, or pass "
                "`--codex-bin` / `CODEX_BIN` to an executable path instead of a `.ps1` shim."
            )
        return resolved
    raise RuntimeError(
        "Unable to locate a runnable codex executable. "
        "Ensure `codex` is on PATH or pass `--codex-bin` / set `CODEX_BIN` "
        "to an executable path. PowerShell alias/function wrappers are not supported by "
        "the Python runner."
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
    return os.environ.get("CODEX_REVIEW_FORCE_UNELEVATED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


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
    result = run_command(
        ["git", "diff", "--no-index", "--", os.devnull, relative_path],
        repo_root,
    )
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


def load_prompt_text(prompt_root: Path, cycle_type: str, substitutions: dict[str, str]) -> str:
    core_path = prompt_root / "core.md"
    phase_path = prompt_root / "phases" / f"{cycle_type}.md"
    preset_path = prompt_root / "preset.md"
    required = [core_path, phase_path]
    missing = [path for path in required if not path.is_file()]
    if missing:
        legacy_prompt_path = prompt_root.parent / "codex_impl_review.md"
        if legacy_prompt_path.is_file() and not prompt_root.exists():
            prompt_text = read_text_strict(legacy_prompt_path)
            for placeholder, value in substitutions.items():
                prompt_text = prompt_text.replace(placeholder, value)
            return prompt_text
        raise FileNotFoundError(
            "Missing required prompt files:\n" + "\n".join(str(path) for path in missing)
        )

    prompt_parts = [read_text_strict(core_path), read_text_strict(phase_path)]
    if preset_path.is_file():
        prompt_parts.append(read_text_strict(preset_path))
    prompt_text = "\n\n".join(part.strip() for part in prompt_parts if part.strip())
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
    impl_review["cycle"] = int(impl_review.get("quality_cycle", legacy_cycle) or 0)

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


def get_phase_cycle(state: dict[str, Any], cycle_type: str) -> int:
    impl_review = state["current"]["impl_review"]
    return int(impl_review.get(f"{cycle_type}_cycle", 0) or 0)


def set_phase_cycle(state: dict[str, Any], cycle_type: str, value: int) -> None:
    impl_review = state["current"]["impl_review"]
    impl_review[f"{cycle_type}_cycle"] = value
    if cycle_type == "quality":
        impl_review["cycle"] = value


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


def build_legacy_review_text(review_text: str, cycle_type: str, phase_output_path: Path) -> str:
    normalized = review_text.rstrip() + "\n"
    if cycle_type == "quality":
        return normalized
    return (
        f"Cycle type: {cycle_type}\n"
        f"Canonical phase output: {phase_output_path.name}\n\n"
        f"{normalized}"
    )


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
    task_summary = (
        args.task_description.strip()
        if args.task_description.strip()
        else f"Review changes in {', '.join(target_files)}"
    )
    substitutions = {
        "$TASK_DESCRIPTION": task_summary,
        "$FILE_LIST": ", ".join(target_files),
        "$CYCLE_TYPE": args.cycle_type,
        "$REVIEW_UNIT": args.review_unit,
    }
    prompt_text = load_prompt_text(paths.prompt_root, args.cycle_type, substitutions)

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

    if args.review_unit != "task":
        context_inputs = [
            ("plan.md", paths.context_dir / "plan.md"),
            ("tasks.md", paths.context_dir / "tasks.md"),
            ("implementation_gap_audit.md", paths.context_dir / "implementation_gap_audit.md"),
        ]
        for title, path in context_inputs:
            if path.is_file():
                append_section(sections, title, read_text_strict(path))

    append_section(sections, "git diff", get_git_diff(paths.repo_root, target_files))

    for relative_path in target_files:
        full_path = paths.repo_root / Path(relative_path)
        if full_path.is_file():
            append_section(sections, f"file: {relative_path}", safe_read_project_file(full_path))

    for relative_path in dependency_files:
        full_path = paths.repo_root / Path(relative_path)
        if full_path.is_file():
            append_section(sections, f"dependency: {relative_path}", safe_read_project_file(full_path))

    previous_review_used = False
    if not args.no_previous:
        previous_review_path = paths.phase_output_path
        if (
            not previous_review_path.is_file()
            and args.cycle_type == "quality"
            and paths.latest_context_output_path.is_file()
            and not (paths.context_dir / "codex_impl_review.alignment.md").is_file()
            and not (paths.context_dir / "codex_impl_review.verification.md").is_file()
        ):
            previous_review_path = paths.latest_context_output_path
        if previous_review_path.is_file():
            append_section(sections, "Previous Review", read_text_strict(previous_review_path))
            previous_review_used = True

    bundle_text = "\n".join(sections).rstrip() + "\n"
    return bundle_text, target_files, dependency_files, previous_review_used, task_summary


def invoke_codex_review(
    codex_bin: str,
    bundle_text: str,
    repo_root: Path,
    timeout_sec: int,
    model: str,
    reasoning_effort: str,
) -> tuple[str, str]:
    codex_exec = resolve_codex_executable(codex_bin)
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
                if stderr:
                    stderr = (
                        stderr
                        + "\nCodex elevated Windows sandbox failed; retried with "
                        'windows.sandbox="unelevated".'
                    )
                else:
                    stderr = (
                        'Codex elevated Windows sandbox failed; retried with '
                        'windows.sandbox="unelevated".'
                    )
            return stdout, stderr

        detail = get_result_detail(result, codex_exec, timeout_sec)
        last_error = detail
        last_stderr = stderr
        if (
            label == "default"
            and is_windows_host()
            and should_retry_unelevated(stderr, stdout)
        ):
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
        "cycle_type": args.cycle_type,
        "review_unit": args.review_unit,
        "current_cycle": current_cycle,
        "task_description": task_summary,
        "target_files": list(target_files),
        "dependency_files": list(dependency_files),
        "previous_review_used": previous_review_used,
        "prompt_root": str(paths.prompt_root),
        "bundle_path": str(bundle_path),
        "phase_output_path": str(paths.phase_output_path),
        "latest_context_output_path": str(paths.latest_context_output_path),
        "latest_review_output_path": str(paths.latest_review_output_path),
        "sessions_path": str(paths.sessions_path),
        "bundle_sha256": compute_bundle_hash(bundle_text),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "verdict": verdict,
        "error": error,
        "stderr": stderr_text,
        "codex_bin": args.codex_bin,
        "resolved_codex_bin": resolved_codex_bin,
        "dry_run": args.dry_run,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path.cwd().resolve()
    paths = RunnerPaths.from_repo_root(
        repo_root,
        args.cycle_type,
        args.prompt_root,
        args.agents_root,
    )

    bundle_text = ""
    target_files: list[str] = []
    dependency_files: list[str] = []
    previous_review_used = False
    task_summary = ""
    resolved_codex_bin: str | None = None
    current_cycle = 0
    sessions_state: dict[str, Any] | None = None
    bundle_path = paths.bundle_path

    try:
        sessions_state = read_sessions_state(paths.sessions_path)
        current_cycle = get_phase_cycle(sessions_state, args.cycle_type) + 1
        bundle_text, target_files, dependency_files, previous_review_used, task_summary = build_bundle(
            args,
            paths,
        )
        bundle_path = write_bundle_text(paths.bundle_path, bundle_text, repo_root)
        if args.dump_bundle:
            dump_path = resolve_optional_path(args.dump_bundle, repo_root)
            write_text(dump_path, bundle_text)

        debug_log(args.debug, f"repo_root={paths.repo_root}")
        debug_log(args.debug, f"prompt_root={paths.prompt_root}")
        debug_log(args.debug, f"cycle_type={args.cycle_type} review_unit={args.review_unit}")
        debug_log(args.debug, f"target_files={target_files}")
        debug_log(args.debug, f"dependency_files={dependency_files}")
        debug_log(args.debug, f"previous_review_used={previous_review_used}")
        debug_log(args.debug, f"model={args.model} reasoning_effort={args.reasoning_effort}")

        if args.dry_run:
            if args.write_trace:
                trace_path = resolve_optional_path(args.write_trace, repo_root)
                payload = build_trace_payload(
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
                    resolved_codex_bin=resolved_codex_bin,
                )
                write_text(trace_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            print("MODE: DRY-RUN")
            print(f"Cycle type: {args.cycle_type}")
            print(f"Review unit: {args.review_unit}")
            print(f"Model: {args.model}")
            print(f"ReasoningEffort: {args.reasoning_effort}")
            print(f"Bundle: {bundle_path}")
            if args.dump_bundle:
                print(f"Bundle copy: {resolve_optional_path(args.dump_bundle, repo_root)}")
            if args.write_trace:
                print(f"Trace: {resolve_optional_path(args.write_trace, repo_root)}")
            return 0

        resolved_codex_bin = resolve_codex_executable(args.codex_bin)
        debug_log(args.debug, f"codex_bin={args.codex_bin}")
        debug_log(args.debug, f"resolved_codex_bin={resolved_codex_bin}")

        review_text, stderr_text = invoke_codex_review(
            resolved_codex_bin,
            bundle_text,
            repo_root,
            args.review_timeout_sec,
            args.model,
            args.reasoning_effort,
        )
        if args.debug and stderr_text:
            debug_log(args.debug, stderr_text)

        verdict = determine_verdict(review_text)
        if verdict is None:
            review_text = review_text.rstrip() + "\n\nVERDICT: CONDITIONAL\n"
            verdict = "CONDITIONAL"

        review_text = review_text.rstrip() + "\n"
        write_text(paths.phase_output_path, review_text)
        legacy_review_text = build_legacy_review_text(
            review_text,
            args.cycle_type,
            paths.phase_output_path,
        )
        write_text(paths.latest_context_output_path, legacy_review_text)
        write_text(paths.latest_review_output_path, legacy_review_text)

        set_phase_cycle(sessions_state, args.cycle_type, current_cycle)
        if verdict == "APPROVED":
            set_phase_cycle(sessions_state, args.cycle_type, 0)
            sessions_state.setdefault("reviews", []).append(
                {
                    "kind": "impl-cycle-review",
                    "cycle_type": args.cycle_type,
                    "cycle": current_cycle,
                    "date": datetime.now(timezone.utc).astimezone().isoformat(),
                    "verdict": verdict,
                }
            )
        write_sessions_state(paths.sessions_path, sessions_state)

        if args.write_trace:
            trace_path = resolve_optional_path(args.write_trace, repo_root)
            payload = build_trace_payload(
                args,
                paths,
                bundle_path=bundle_path,
                current_cycle=current_cycle,
                task_summary=task_summary,
                target_files=target_files,
                dependency_files=dependency_files,
                previous_review_used=previous_review_used,
                bundle_text=bundle_text,
                status="completed",
                verdict=verdict,
                stderr_text=stderr_text,
                resolved_codex_bin=resolved_codex_bin,
            )
            write_text(trace_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

        print(f"VERDICT: {verdict}")
        print(f"Cycle: {current_cycle}")
        print(f"Cycle type: {args.cycle_type}")
        print(f"Review unit: {args.review_unit}")
        print(f"Model: {args.model}")
        print(f"ReasoningEffort: {args.reasoning_effort}")
        print(f"Codex: {resolved_codex_bin}")
        print(f"Bundle: {bundle_path}")
        print(f"Review: {paths.phase_output_path}")
        print(f"Sessions: {paths.sessions_path}")
        if args.write_trace:
            print(f"Trace: {resolve_optional_path(args.write_trace, repo_root)}")
        return 0
    except Exception as exc:
        if args.write_trace:
            trace_path = resolve_optional_path(args.write_trace, repo_root)
            payload = build_trace_payload(
                args,
                paths,
                bundle_path=bundle_path,
                current_cycle=current_cycle,
                task_summary=task_summary,
                target_files=target_files,
                dependency_files=dependency_files,
                previous_review_used=previous_review_used,
                bundle_text=bundle_text,
                status="error",
                error=str(exc),
                resolved_codex_bin=resolved_codex_bin,
            )
            write_text(trace_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
