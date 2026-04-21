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
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run-codex-impl-cycle.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_codex_impl_cycle", SCRIPT_PATH)
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


class RunCodexImplCycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner_module()
        temp_root = REPO_ROOT / "tmp" / "test-run-codex-impl-cycle"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.repo_root = temp_root / f"case-{uuid.uuid4().hex}"
        self.repo_root.mkdir()
        self._create_repo_layout()

    def tearDown(self) -> None:
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def _create_repo_layout(self) -> None:
        prompt_root = self.repo_root / "agents" / "prompts" / "impl-review"
        (prompt_root / "phases").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "agents" / "context").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "agents" / "reviews").mkdir(parents=True, exist_ok=True)

        (prompt_root / "core.md").write_text(
            "Task=$TASK_DESCRIPTION\nFiles=$FILE_LIST\nCycle=$CYCLE_TYPE\nUnit=$REVIEW_UNIT\n",
            encoding="utf-8",
        )
        (prompt_root / "phases" / "alignment.md").write_text(
            "Alignment phase prompt",
            encoding="utf-8",
        )
        (prompt_root / "phases" / "verification.md").write_text(
            "Verification phase prompt",
            encoding="utf-8",
        )
        (prompt_root / "phases" / "quality.md").write_text(
            "Quality phase prompt",
            encoding="utf-8",
        )
        (prompt_root / "preset.md").write_text("Preset prompt", encoding="utf-8")

        context_dir = self.repo_root / "agents" / "context"
        (context_dir / "plan.md").write_text("Plan body", encoding="utf-8")
        (context_dir / "tasks.md").write_text("Task body", encoding="utf-8")
        (context_dir / "implementation_gap_audit.md").write_text("Gap body", encoding="utf-8")
        (context_dir / "codex_impl_review.alignment.md").write_text(
            "Previous alignment review",
            encoding="utf-8",
        )

        (self.repo_root / "src").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
        (self.repo_root / "src" / "dep.py").write_text("VALUE = 1\n", encoding="utf-8")

    def test_build_bundle_uses_phase_specific_previous_review(self) -> None:
        args = self.runner.parse_args(
            [
                "--cycle-type",
                "alignment",
                "--review-unit",
                "task",
                "--task-description",
                "Check impl cycle",
                "--files",
                "src/main.py",
                "--include-files",
                "src/dep.py",
            ]
        )
        paths = self.runner.RunnerPaths.from_repo_root(self.repo_root, "alignment", None, "agents")

        with mock.patch.object(self.runner, "get_git_diff", return_value="diff --git a/src/main.py"):
            bundle_text, targets, deps, previous_used, task_summary = self.runner.build_bundle(
                args,
                paths,
            )

        self.assertEqual(targets, ["src/main.py"])
        self.assertEqual(deps, ["src/dep.py"])
        self.assertTrue(previous_used)
        self.assertEqual(task_summary, "Check impl cycle")
        self.assertIn("Alignment phase prompt", bundle_text)
        self.assertIn("Preset prompt", bundle_text)
        self.assertNotIn("Plan body", bundle_text)
        self.assertNotIn("Task body", bundle_text)
        self.assertNotIn("Gap body", bundle_text)
        self.assertIn("diff --git a/src/main.py", bundle_text)
        self.assertIn("Previous alignment review", bundle_text)

    def test_build_bundle_includes_context_for_batch_review_unit(self) -> None:
        args = self.runner.parse_args(
            [
                "--cycle-type",
                "alignment",
                "--review-unit",
                "batch",
                "--task-description",
                "Check impl cycle batch",
                "--files",
                "src/main.py",
            ]
        )
        paths = self.runner.RunnerPaths.from_repo_root(self.repo_root, "alignment", None, "agents")

        with mock.patch.object(self.runner, "get_git_diff", return_value="diff --git a/src/main.py"):
            bundle_text, _, _, _, _ = self.runner.build_bundle(args, paths)

        self.assertIn("Plan body", bundle_text)
        self.assertIn("Task body", bundle_text)
        self.assertIn("Gap body", bundle_text)

    def test_build_bundle_quality_falls_back_to_legacy_previous_review(self) -> None:
        args = self.runner.parse_args(
            [
                "--cycle-type",
                "quality",
                "--task-description",
                "Quality fallback",
                "--files",
                "src/main.py",
            ]
        )
        paths = self.runner.RunnerPaths.from_repo_root(self.repo_root, "quality", None, "agents")
        legacy_path = self.repo_root / "agents" / "context" / "codex_impl_review.md"
        legacy_path.write_text("Legacy quality review", encoding="utf-8")
        (self.repo_root / "agents" / "context" / "codex_impl_review.alignment.md").unlink()

        with mock.patch.object(self.runner, "get_git_diff", return_value="quality diff"):
            bundle_text, _, _, previous_used, _ = self.runner.build_bundle(args, paths)

        self.assertTrue(previous_used)
        self.assertIn("Legacy quality review", bundle_text)

    def test_build_bundle_uses_legacy_prompt_when_phase_prompts_are_absent(self) -> None:
        shutil.rmtree(self.repo_root / "agents" / "prompts" / "impl-review")
        (self.repo_root / "agents" / "prompts" / "codex_impl_review.md").write_text(
            "Legacy prompt for $TASK_DESCRIPTION over $FILE_LIST",
            encoding="utf-8",
        )
        args = self.runner.parse_args(
            [
                "--cycle-type",
                "alignment",
                "--task-description",
                "Legacy prompt task",
                "--files",
                "src/main.py",
            ]
        )
        paths = self.runner.RunnerPaths.from_repo_root(self.repo_root, "alignment", None, "agents")

        with mock.patch.object(self.runner, "get_git_diff", return_value="legacy diff"):
            bundle_text, _, _, _, _ = self.runner.build_bundle(args, paths)

        self.assertIn("Legacy prompt for Legacy prompt task over src/main.py", bundle_text)

    def test_build_bundle_does_not_hide_partial_phase_prompt_layout(self) -> None:
        (self.repo_root / "agents" / "prompts" / "impl-review" / "phases" / "alignment.md").unlink()
        (self.repo_root / "agents" / "prompts" / "codex_impl_review.md").write_text(
            "Legacy prompt for $TASK_DESCRIPTION over $FILE_LIST",
            encoding="utf-8",
        )
        args = self.runner.parse_args(
            [
                "--cycle-type",
                "alignment",
                "--task-description",
                "Partial prompt task",
                "--files",
                "src/main.py",
            ]
        )
        paths = self.runner.RunnerPaths.from_repo_root(self.repo_root, "alignment", None, "agents")

        with mock.patch.object(self.runner, "get_git_diff", return_value="legacy diff"):
            with self.assertRaises(FileNotFoundError):
                self.runner.build_bundle(args, paths)

    def test_ensure_sessions_shape_migrates_legacy_cycle(self) -> None:
        state = self.runner.ensure_sessions_shape({"current": {"impl_review": {"cycle": 4}}})
        impl_review = state["current"]["impl_review"]
        self.assertEqual(impl_review["quality_cycle"], 4)
        self.assertEqual(impl_review["cycle"], 4)
        self.assertEqual(impl_review["alignment_cycle"], 0)
        self.assertEqual(impl_review["verification_cycle"], 0)
        self.assertEqual(impl_review["macro_cycle"], 0)

    def test_main_dry_run_writes_bundle_and_trace(self) -> None:
        trace_path = self.repo_root / "tmp" / "trace.json"
        bundle_copy = self.repo_root / "tmp" / "bundle.md"

        with chdir(self.repo_root), mock.patch.object(
            self.runner,
            "get_git_diff",
            return_value="dry-run diff",
        ):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "alignment",
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
        self.assertEqual(trace["cycle_type"], "alignment")
        self.assertEqual(trace["task_description"], "Dry run")
        self.assertEqual(trace["model"], "gpt-5.4")
        self.assertEqual(trace["reasoning_effort"], "high")

    def test_main_dry_run_falls_back_when_context_bundle_is_unwritable(self) -> None:
        trace_path = self.repo_root / "tmp" / "fallback-trace.json"
        expected_bundle = self.repo_root / "agents" / "context" / "_codex_input.tmp"
        original_write_text = self.runner.write_text
        state = {"raised": False}

        def fake_write_text(path: Path, content: str) -> None:
            if path == expected_bundle and not state["raised"]:
                state["raised"] = True
                raise PermissionError("bundle locked")
            original_write_text(path, content)

        with chdir(self.repo_root), mock.patch.object(
            self.runner,
            "get_git_diff",
            return_value="dry-run diff",
        ), mock.patch.object(
            self.runner,
            "write_text",
            side_effect=fake_write_text,
        ):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "alignment",
                    "--task-description",
                    "Dry run fallback",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                    "--dry-run",
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        fallback_dir = self.repo_root / "tmp" / "impl-cycle-bundles"
        fallback_files = list(fallback_dir.glob("_codex_input*.tmp"))
        self.assertEqual(len(fallback_files), 1)
        self.assertTrue(trace_path.is_file())
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "dry-run")
        self.assertEqual(Path(trace["bundle_path"]), fallback_files[0])

    def test_main_writes_phase_outputs_and_resets_cycle_on_approved(self) -> None:
        trace_path = self.repo_root / "tmp" / "approved-trace.json"

        with chdir(self.repo_root), mock.patch.object(
            self.runner,
            "get_git_diff",
            return_value="quality diff",
        ), mock.patch.object(
            self.runner,
            "resolve_codex_executable",
            return_value="/usr/bin/codex",
        ), mock.patch.object(
            self.runner,
            "invoke_codex_review",
            return_value=("### Findings\n\nNone.\n\nVERDICT: APPROVED", ""),
        ):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "quality",
                    "--task-description",
                    "Approved run",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        phase_output = self.repo_root / "agents" / "context" / "codex_impl_review.quality.md"
        latest_output = self.repo_root / "agents" / "context" / "codex_impl_review.md"
        shared_output = self.repo_root / "agents" / "reviews" / "impl-review.md"
        sessions_path = self.repo_root / "agents" / "reviews" / "sessions.json"

        self.assertTrue(phase_output.is_file())
        self.assertTrue(latest_output.is_file())
        self.assertTrue(shared_output.is_file())
        self.assertTrue(trace_path.is_file())

        sessions = json.loads(sessions_path.read_text(encoding="utf-8"))
        self.assertEqual(sessions["current"]["impl_review"]["quality_cycle"], 0)
        self.assertEqual(sessions["current"]["impl_review"]["cycle"], 0)
        self.assertEqual(len(sessions["reviews"]), 1)
        self.assertEqual(sessions["reviews"][0]["cycle_type"], "quality")
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["resolved_codex_bin"], "/usr/bin/codex")

    def test_main_alignment_run_does_not_overwrite_shared_review_artifacts(self) -> None:
        context_output = self.repo_root / "agents" / "context" / "codex_impl_review.md"
        review_output = self.repo_root / "agents" / "reviews" / "impl-review.md"
        context_output.write_text("Legacy shared review", encoding="utf-8")
        review_output.write_text("Legacy shared review", encoding="utf-8")

        with chdir(self.repo_root), mock.patch.object(
            self.runner,
            "get_git_diff",
            return_value="alignment diff",
        ), mock.patch.object(
            self.runner,
            "resolve_codex_executable",
            return_value="/usr/bin/codex",
        ), mock.patch.object(
            self.runner,
            "invoke_codex_review",
            return_value=("### Findings\n\nNone.\n\nVERDICT: APPROVED", ""),
        ):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "alignment",
                    "--task-description",
                    "Alignment run",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                ]
            )

        self.assertEqual(exit_code, 0)
        shared_context = context_output.read_text(encoding="utf-8")
        shared_review = review_output.read_text(encoding="utf-8")
        self.assertIn("Cycle type: alignment", shared_context)
        self.assertIn("Canonical phase output: codex_impl_review.alignment.md", shared_context)
        self.assertIn("VERDICT: APPROVED", shared_context)
        self.assertEqual(shared_context, shared_review)
        phase_output = self.repo_root / "agents" / "context" / "codex_impl_review.alignment.md"
        self.assertTrue(phase_output.is_file())

    def test_resolve_codex_executable_rejects_powershell_wrapper_script(self) -> None:
        with mock.patch.object(self.runner.shutil, "which", return_value="C:/tools/codex.ps1"):
            with self.assertRaisesRegex(RuntimeError, "PowerShell script wrapper"):
                self.runner.resolve_codex_executable("codex")

    def test_get_changed_files_includes_unstaged_staged_and_untracked(self) -> None:
        responses = [
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="src/unstaged.py\nsrc/shared.py\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="src/staged.py\nsrc/shared.py\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="src/untracked.py\n",
                stderr="",
            ),
        ]

        with mock.patch.object(self.runner, "run_command", side_effect=responses):
            changed = self.runner.get_changed_files(self.repo_root)

        self.assertEqual(
            changed,
            ["src/unstaged.py", "src/shared.py", "src/staged.py", "src/untracked.py"],
        )

    def test_get_changed_files_includes_deleted_paths(self) -> None:
        responses = [
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="src/deleted.py\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        with mock.patch.object(self.runner, "run_command", side_effect=responses):
            changed = self.runner.get_changed_files(self.repo_root)

        self.assertEqual(changed, ["src/deleted.py"])

    def test_invoke_codex_review_retries_unelevated_on_windows_sandbox_failure(self) -> None:
        default_failure = self.runner.ReviewAttemptResult(
            returncode=1,
            stdout="",
            stderr="CreateProcessAsUserW failed",
            timed_out=False,
        )
        unelevated_success = self.runner.ReviewAttemptResult(
            returncode=0,
            stdout="VERDICT: APPROVED\n",
            stderr="",
            timed_out=False,
        )

        with mock.patch.object(
            self.runner,
            "resolve_codex_executable",
            return_value="/usr/bin/codex",
        ), mock.patch.object(
            self.runner,
            "is_windows_host",
            return_value=True,
        ), mock.patch.object(
            self.runner,
            "prefer_unelevated_retry",
            return_value=False,
        ), mock.patch.object(
            self.runner,
            "fix_plugin_prompts_if_available",
            return_value=[],
        ), mock.patch.object(
            self.runner,
            "run_codex_review_attempt",
            side_effect=[default_failure, unelevated_success],
        ) as attempt_mock:
            stdout, stderr = self.runner.invoke_codex_review(
                "codex",
                "bundle",
                self.repo_root,
                60,
                "gpt-5.4",
                "high",
            )

        self.assertIn("VERDICT: APPROVED", stdout)
        self.assertIn('windows.sandbox="unelevated"', stderr)
        self.assertEqual(attempt_mock.call_count, 2)
        self.assertFalse(attempt_mock.call_args_list[0].kwargs["unelevated"])
        self.assertTrue(attempt_mock.call_args_list[1].kwargs["unelevated"])

    def test_invoke_codex_review_retries_unelevated_after_timeout(self) -> None:
        timeout_failure = self.runner.ReviewAttemptResult(
            returncode=-1,
            stdout="",
            stderr="CreateProcessAsUserW failed",
            timed_out=True,
        )
        unelevated_success = self.runner.ReviewAttemptResult(
            returncode=0,
            stdout="VERDICT: APPROVED\n",
            stderr="",
            timed_out=False,
        )

        with mock.patch.object(
            self.runner,
            "resolve_codex_executable",
            return_value="/usr/bin/codex",
        ), mock.patch.object(
            self.runner,
            "is_windows_host",
            return_value=True,
        ), mock.patch.object(
            self.runner,
            "prefer_unelevated_retry",
            return_value=False,
        ), mock.patch.object(
            self.runner,
            "fix_plugin_prompts_if_available",
            return_value=[],
        ), mock.patch.object(
            self.runner,
            "run_codex_review_attempt",
            side_effect=[timeout_failure, unelevated_success],
        ) as attempt_mock:
            stdout, _ = self.runner.invoke_codex_review(
                "codex",
                "bundle",
                self.repo_root,
                60,
                "gpt-5.4",
                "high",
            )

        self.assertIn("VERDICT: APPROVED", stdout)
        self.assertEqual(attempt_mock.call_count, 2)
        self.assertFalse(attempt_mock.call_args_list[0].kwargs["unelevated"])
        self.assertTrue(attempt_mock.call_args_list[1].kwargs["unelevated"])

    def test_invoke_codex_review_does_not_retry_plain_timeout(self) -> None:
        timeout_failure = self.runner.ReviewAttemptResult(
            returncode=-1,
            stdout="",
            stderr="",
            timed_out=True,
        )

        with mock.patch.object(
            self.runner,
            "resolve_codex_executable",
            return_value="/usr/bin/codex",
        ), mock.patch.object(
            self.runner,
            "is_windows_host",
            return_value=True,
        ), mock.patch.object(
            self.runner,
            "prefer_unelevated_retry",
            return_value=False,
        ), mock.patch.object(
            self.runner,
            "fix_plugin_prompts_if_available",
            return_value=[],
        ), mock.patch.object(
            self.runner,
            "run_codex_review_attempt",
            return_value=timeout_failure,
        ) as attempt_mock:
            with self.assertRaisesRegex(RuntimeError, "timed out after 60 seconds"):
                self.runner.invoke_codex_review(
                    "codex",
                    "bundle",
                    self.repo_root,
                    60,
                    "gpt-5.4",
                    "high",
                )

        self.assertEqual(attempt_mock.call_count, 1)

    def test_get_git_diff_includes_index_and_untracked_sections(self) -> None:
        with mock.patch.object(
            self.runner,
            "run_command",
            side_effect=[
                subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
                subprocess.CompletedProcess(args=[], returncode=0, stdout="cached diff", stderr=""),
                subprocess.CompletedProcess(args=[], returncode=0, stdout="?? src/new.py\n", stderr=""),
                subprocess.CompletedProcess(args=[], returncode=1, stdout="untracked diff", stderr=""),
            ],
        ):
            diff_text = self.runner.get_git_diff(self.repo_root, ["src/main.py", "src/new.py"])

        self.assertIn("## Index diff", diff_text)
        self.assertIn("cached diff", diff_text)
        self.assertIn("## Untracked diff: src/new.py", diff_text)
        self.assertIn("untracked diff", diff_text)

    def test_main_errors_when_codex_executable_is_missing(self) -> None:
        sessions_path = self.repo_root / "agents" / "reviews" / "sessions.json"
        with chdir(self.repo_root), mock.patch.object(
            self.runner,
            "get_git_diff",
            return_value="quality diff",
        ), mock.patch.object(
            self.runner,
            "resolve_codex_executable",
            side_effect=RuntimeError("codex missing"),
        ):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "quality",
                    "--task-description",
                    "Missing codex",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                ]
            )

        self.assertEqual(exit_code, 1)
        if sessions_path.exists():
            sessions = json.loads(sessions_path.read_text(encoding="utf-8"))
            self.assertEqual(sessions["current"]["impl_review"]["quality_cycle"], 0)
            self.assertEqual(sessions["current"]["impl_review"]["cycle"], 0)

    def test_main_does_not_advance_cycle_when_review_invocation_fails(self) -> None:
        sessions_path = self.repo_root / "agents" / "reviews" / "sessions.json"

        with chdir(self.repo_root), mock.patch.object(
            self.runner,
            "get_git_diff",
            return_value="quality diff",
        ), mock.patch.object(
            self.runner,
            "resolve_codex_executable",
            return_value="/usr/bin/codex",
        ), mock.patch.object(
            self.runner,
            "invoke_codex_review",
            side_effect=RuntimeError("review failed"),
        ):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "quality",
                    "--task-description",
                    "Invocation failure",
                    "--files",
                    "src/main.py",
                    "--agents-root",
                    "agents",
                ]
            )

        self.assertEqual(exit_code, 1)
        if sessions_path.exists():
            sessions = json.loads(sessions_path.read_text(encoding="utf-8"))
            self.assertEqual(sessions["current"]["impl_review"]["quality_cycle"], 0)
            self.assertEqual(sessions["current"]["impl_review"]["cycle"], 0)

    def test_main_writes_trace_even_when_bundle_build_fails(self) -> None:
        trace_path = self.repo_root / "tmp" / "error-trace.json"

        with chdir(self.repo_root), mock.patch.object(
            self.runner,
            "build_bundle",
            side_effect=RuntimeError("bundle failed"),
        ):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "quality",
                    "--agents-root",
                    "agents",
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 1)
        self.assertTrue(trace_path.is_file())
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "error")
        self.assertEqual(trace["error"], "bundle failed")

    def test_build_codex_review_args_includes_model_defaults(self) -> None:
        args = self.runner.build_codex_review_args(
            codex_exec="codex",
            model="gpt-5.4",
            reasoning_effort="high",
            unelevated=True,
        )

        self.assertIn('model="gpt-5.4"', args)
        self.assertIn('model_reasoning_effort="high"', args)
        self.assertIn('windows.sandbox="unelevated"', args)

    def test_main_writes_trace_when_sessions_state_is_invalid(self) -> None:
        trace_path = self.repo_root / "tmp" / "session-error-trace.json"
        sessions_path = self.repo_root / "agents" / "reviews" / "sessions.json"
        sessions_path.write_text('{"current": {"impl_review": {"quality_cycle": "bad"}}}', encoding="utf-8")

        with chdir(self.repo_root):
            exit_code = self.runner.main(
                [
                    "--cycle-type",
                    "quality",
                    "--agents-root",
                    "agents",
                    "--write-trace",
                    str(trace_path),
                ]
            )

        self.assertEqual(exit_code, 1)
        self.assertTrue(trace_path.is_file())
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "error")
        self.assertIn("invalid literal", trace["error"])


if __name__ == "__main__":
    unittest.main()
