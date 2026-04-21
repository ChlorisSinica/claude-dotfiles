from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run-codex-impl-review.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_codex_impl_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def chdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class RunCodexImplReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner_module()
        temp_root = REPO_ROOT / "tmp" / "test-run-codex-impl-review"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.repo_root = temp_root / f"case-{uuid.uuid4().hex}"
        self.repo_root.mkdir()
        self._create_repo_layout()

    def tearDown(self) -> None:
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def _create_repo_layout(self) -> None:
        prompt_dir = self.repo_root / "agents" / "prompts"
        context_dir = self.repo_root / "agents" / "context"
        reviews_dir = self.repo_root / "agents" / "reviews"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        context_dir.mkdir(parents=True, exist_ok=True)
        reviews_dir.mkdir(parents=True, exist_ok=True)

        (prompt_dir / "codex_impl_review.md").write_text(
            "Prompt for $TASK_DESCRIPTION over $FILE_LIST",
            encoding="utf-8",
        )
        (context_dir / "plan.md").write_text("Plan body\n" * 4, encoding="utf-8")
        (context_dir / "tasks.md").write_text("Task body\n" * 4, encoding="utf-8")
        (context_dir / "codex_impl_review.md").write_text(
            "### Findings\n\n- [P1] Existing issue\n\nVERDICT: CONDITIONAL\n",
            encoding="utf-8",
        )
        (self.repo_root / "src").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
        (self.repo_root / "src" / "dep.py").write_text("VALUE = 1\n", encoding="utf-8")

    def test_build_bundle_uses_prompt_and_previous_review_summary(self) -> None:
        args = self.runner.parse_args(
            [
                "--task-description",
                "Check impl review",
                "--files",
                "src/main.py",
                "--include-files",
                "src/dep.py",
            ]
        )
        paths = self.runner.RunnerPaths.from_repo_root(self.repo_root, None, "agents")

        with mock.patch.object(self.runner, "get_git_diff", return_value="## Working tree diff\nmock diff"):
            bundle_text, targets, deps, previous_used, task_summary = self.runner.build_bundle(args, paths)

        self.assertEqual(targets, ["src/main.py"])
        self.assertEqual(deps, ["src/dep.py"])
        self.assertTrue(previous_used)
        self.assertEqual(task_summary, "Check impl review")
        self.assertIn("Prompt for Check impl review over src/main.py", bundle_text)
        self.assertIn("model = gpt-5.4", bundle_text)
        self.assertIn("mock diff", bundle_text)
        self.assertNotIn("Plan body", bundle_text)
        self.assertNotIn("Task body", bundle_text)
        self.assertIn("### Findings", bundle_text)
        self.assertIn("VERDICT: CONDITIONAL", bundle_text)

    def test_main_dry_run_writes_bundle_and_trace(self) -> None:
        trace_path = self.repo_root / "tmp" / "trace.json"
        bundle_copy = self.repo_root / "tmp" / "bundle.md"

        with chdir(self.repo_root), mock.patch.object(self.runner, "get_git_diff", return_value="dry-run diff"):
            exit_code = self.runner.main(
                [
                    "--task-description",
                    "Dry run",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                    "--dry-run",
                    "--dump-bundle",
                    str(bundle_copy),
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.repo_root / "agents" / "context" / "_codex_input.tmp").is_file())
        self.assertTrue(bundle_copy.is_file())
        self.assertTrue(trace_path.is_file())
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "dry-run")
        self.assertEqual(trace["model"], "gpt-5.4")
        self.assertEqual(trace["reasoning_effort"], "high")

    def test_write_bundle_text_falls_back_when_primary_is_locked(self) -> None:
        bundle_path = self.repo_root / "agents" / "context" / "_codex_input.tmp"
        original_write = self.runner.write_text
        state = {"raised": False}

        def flaky_write(path: Path, content: str) -> None:
            if path == bundle_path and not state["raised"]:
                state["raised"] = True
                raise PermissionError("locked")
            original_write(path, content)

        with mock.patch.object(self.runner, "write_text", side_effect=flaky_write):
            actual_path = self.runner.write_bundle_text(bundle_path, "bundle body", self.repo_root)

        self.assertNotEqual(actual_path, bundle_path)
        self.assertTrue(actual_path.is_file())
        self.assertEqual(actual_path.read_text(encoding="utf-8"), "bundle body")
        self.assertIn(str(self.repo_root / "tmp" / "impl-review-bundles"), str(actual_path))

    def test_main_preflight_failure_does_not_increment_cycle(self) -> None:
        trace_path = self.repo_root / "tmp" / "failure-trace.json"

        with chdir(self.repo_root), mock.patch.object(self.runner, "get_git_diff", return_value="failure diff"), mock.patch.object(
            self.runner, "resolve_codex_executable", side_effect=RuntimeError("missing codex")
        ):
            exit_code = self.runner.main(
                [
                    "--task-description",
                    "Preflight failure",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 1)
        state = self.runner.read_sessions_state(self.repo_root / "agents" / "reviews" / "sessions.json")
        self.assertEqual(state["current"]["impl_review"]["cycle"], 0)
        self.assertEqual(state["current"]["impl_review"]["quality_cycle"], 0)
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "failed")
        self.assertEqual(trace["error"], "missing codex")

    def test_main_review_failure_does_not_increment_cycle(self) -> None:
        trace_path = self.repo_root / "tmp" / "review-failure-trace.json"

        with chdir(self.repo_root), mock.patch.object(self.runner, "get_git_diff", return_value="failure diff"), mock.patch.object(
            self.runner, "resolve_codex_executable", return_value="/usr/bin/codex"
        ), mock.patch.object(
            self.runner, "invoke_codex_review", side_effect=RuntimeError("review failed")
        ):
            exit_code = self.runner.main(
                [
                    "--task-description",
                    "Review failure",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 1)
        state = self.runner.read_sessions_state(self.repo_root / "agents" / "reviews" / "sessions.json")
        self.assertEqual(state["current"]["impl_review"]["cycle"], 0)
        self.assertEqual(state["current"]["impl_review"]["quality_cycle"], 0)
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "failed")
        self.assertEqual(trace["error"], "review failed")

    def test_invoke_codex_review_retries_unelevated_on_windows_sandbox_failure(self) -> None:
        attempts = [
            self.runner.ReviewAttemptResult(returncode=1, stdout="", stderr="windows sandbox failed", timed_out=False),
            self.runner.ReviewAttemptResult(returncode=0, stdout="VERDICT: APPROVED", stderr="", timed_out=False),
        ]

        with mock.patch.object(self.runner, "is_windows_host", return_value=True), mock.patch.object(
            self.runner, "prefer_unelevated_retry", return_value=False
        ), mock.patch.object(self.runner, "fix_plugin_prompts_if_available", return_value=[]), mock.patch.object(
            self.runner, "run_codex_review_attempt", side_effect=attempts
        ):
            stdout, stderr = self.runner.invoke_codex_review(
                codex_exec="codex",
                bundle_text="bundle",
                repo_root=self.repo_root,
                timeout_sec=60,
                model="gpt-5.4",
                reasoning_effort="high",
            )

        self.assertEqual(stdout, "VERDICT: APPROVED")
        self.assertIn('windows.sandbox="unelevated"', stderr)

    def test_main_approved_run_writes_outputs_and_resets_cycle(self) -> None:
        trace_path = self.repo_root / "tmp" / "approved-trace.json"

        with chdir(self.repo_root), mock.patch.object(self.runner, "get_git_diff", return_value="approved diff"), mock.patch.object(
            self.runner, "resolve_codex_executable", return_value="/usr/bin/codex"
        ), mock.patch.object(
            self.runner,
            "invoke_codex_review",
            return_value=("### Findings\n\nNone.\n\nVERDICT: APPROVED", "retry note"),
        ):
            exit_code = self.runner.main(
                [
                    "--task-description",
                    "Approved run",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                    "--model",
                    "gpt-5.4-mini",
                    "--reasoning-effort",
                    "medium",
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.repo_root / "agents" / "context" / "codex_impl_review.md").is_file())
        self.assertTrue((self.repo_root / "agents" / "reviews" / "impl-review.md").is_file())
        state = self.runner.read_sessions_state(self.repo_root / "agents" / "reviews" / "sessions.json")
        self.assertEqual(state["current"]["impl_review"]["cycle"], 0)
        self.assertEqual(state["current"]["impl_review"]["quality_cycle"], 0)
        self.assertEqual(len(state["reviews"]), 1)
        self.assertEqual(state["reviews"][0]["kind"], "impl-review")

        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "ok")
        self.assertEqual(trace["verdict"], "APPROVED")
        self.assertEqual(trace["model"], "gpt-5.4-mini")
        self.assertEqual(trace["reasoning_effort"], "medium")
        self.assertEqual(trace["resolved_codex_bin"], "/usr/bin/codex")

    def test_normalize_repo_paths_rejects_symlink_escape(self) -> None:
        original_resolve = Path.resolve
        link_path = self.repo_root / "src" / "linked.txt"
        external_path = self.repo_root.parent / "outside.txt"

        def fake_resolve(path: Path, *args, **kwargs) -> Path:
            if path == link_path:
                return external_path
            return original_resolve(path, *args, **kwargs)

        with mock.patch("pathlib.Path.resolve", autospec=True, side_effect=fake_resolve):
            with self.assertRaises(ValueError):
                self.runner.normalize_repo_paths(["src/linked.txt"], self.repo_root)
