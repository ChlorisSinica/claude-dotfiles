from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run-verify.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_verify", SCRIPT_PATH)
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


class RunVerifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner_module()
        temp_root = REPO_ROOT / "tmp" / "test-run-verify"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.repo_root = temp_root / f"case-{uuid.uuid4().hex}"
        self.repo_root.mkdir()
        scripts_dir = self.repo_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "verify-config.json").write_text(
            json.dumps(
                {
                    "VERIFY_CMD": "python -m pytest --tb=short -q",
                    "VERIFY_SHELL": "direct",
                    "PRIMARY_LOG_DIR": ".agents/logs/verify",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def test_load_verify_config_reads_file(self) -> None:
        config = self.runner.load_verify_config(self.repo_root / "scripts" / "verify-config.json")
        self.assertEqual(config.command, "python -m pytest --tb=short -q")
        self.assertEqual(config.shell, "direct")

    def test_resolve_shell_command_supports_powershell(self) -> None:
        with mock.patch.object(self.runner.shutil, "which", side_effect=lambda name: "C:/pwsh.exe" if name == "pwsh" else None):
            args, decode_encoding = self.runner.resolve_shell_command("powershell")
        self.assertEqual(args[0], "C:/pwsh.exe")
        self.assertEqual(decode_encoding, "utf-8")

    def test_build_subprocess_args_uses_argv_for_direct_commands(self) -> None:
        args, use_shell, decode_encoding = self.runner.build_subprocess_args(
            self.runner.VerifyConfig(
                command="python -m pytest --tb=short -q",
                shell="direct",
                log_dir=".agents/logs/verify",
            )
        )
        self.assertFalse(use_shell)
        self.assertEqual(args[:3], ["python", "-m", "pytest"])
        self.assertIsNone(decode_encoding)

    def test_build_subprocess_args_prefixes_call_operator_for_quoted_powershell_command(self) -> None:
        with mock.patch.object(self.runner.shutil, "which", side_effect=lambda name: "C:/pwsh.exe" if name == "pwsh" else None):
            args, use_shell, decode_encoding = self.runner.build_subprocess_args(
                self.runner.VerifyConfig(
                    command='"C:/Program Files/AutoHotkey/AutoHotkey.exe" /ErrorStdOut main.ahk',
                    shell="powershell",
                    log_dir=".agents/logs/verify",
                )
            )

        self.assertFalse(use_shell)
        self.assertEqual(args[:-1], ["C:/pwsh.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"])
        self.assertEqual(args[-1], '& "C:/Program Files/AutoHotkey/AutoHotkey.exe" /ErrorStdOut main.ahk')
        self.assertEqual(decode_encoding, "utf-8")

    def test_main_writes_status_and_latest_artifacts(self) -> None:
        completed = mock.Mock(returncode=0, stdout="ok\n", stderr="")
        with chdir(self.repo_root), mock.patch.object(self.runner.subprocess, "run", return_value=completed):
            exit_code = self.runner.main([])

        self.assertEqual(exit_code, 0)
        status_path = self.repo_root / ".agents" / "logs" / "verify" / "latest.status.json"
        log_path = self.repo_root / ".agents" / "logs" / "verify" / "latest.log"
        self.assertTrue(status_path.is_file())
        self.assertTrue(log_path.is_file())
        status = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertTrue(status["ok"])
        self.assertEqual(status["shell"], "direct")

    def test_write_verify_artifacts_uses_unique_history_paths(self) -> None:
        config = self.runner.VerifyConfig(
            command="python -m pytest --tb=short -q",
            shell="direct",
            log_dir=".agents/logs/verify",
        )
        first_log, first_status = self.runner.write_verify_artifacts(
            repo_root=self.repo_root,
            config=config,
            output_text="one\n",
            exit_code=1,
        )
        second_log, second_status = self.runner.write_verify_artifacts(
            repo_root=self.repo_root,
            config=config,
            output_text="two\n",
            exit_code=0,
        )

        self.assertNotEqual(first_log, second_log)
        self.assertNotEqual(first_status, second_status)
        self.assertTrue(first_log.is_file())
        self.assertTrue(second_log.is_file())

    def test_main_reports_shell_resolution_failure(self) -> None:
        config_path = self.repo_root / ".claude" / "scripts" / "verify-config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "VERIFY_CMD": "Get-ChildItem",
                    "VERIFY_SHELL": "powershell",
                    "PRIMARY_LOG_DIR": ".agents/logs/verify",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        with chdir(self.repo_root), mock.patch.object(self.runner.shutil, "which", return_value=None):
            exit_code = self.runner.main([])
        self.assertEqual(exit_code, 1)
        status = json.loads((self.repo_root / ".agents" / "logs" / "verify" / "latest.status.json").read_text(encoding="utf-8"))
        self.assertFalse(status["ok"])

    def test_run_verify_command_decodes_non_utf8_output(self) -> None:
        completed = mock.Mock(returncode=1, stdout=b"\x82\xa0\n", stderr=b"\x83e\x83X\x83g\n")
        with mock.patch.object(self.runner.subprocess, "run", return_value=completed):
            exit_code, output = self.runner.run_verify_command(
                self.runner.VerifyConfig(
                    command="python -m pytest --tb=short -q",
                    shell="bash",
                    log_dir=".agents/logs/verify",
                ),
                self.repo_root,
            )

        self.assertEqual(exit_code, 1)
        self.assertIsInstance(output, str)
        self.assertNotEqual(output, "")

    def test_run_verify_command_decodes_pwsh_output_as_utf8(self) -> None:
        completed = mock.Mock(returncode=0, stdout="日本語\n".encode("utf-8"), stderr=b"")
        with mock.patch.object(self.runner.shutil, "which", side_effect=lambda name: "C:/pwsh.exe" if name == "pwsh" else None):
            with mock.patch.object(self.runner.subprocess, "run", return_value=completed):
                exit_code, output = self.runner.run_verify_command(
                    self.runner.VerifyConfig(
                        command="Write-Output '日本語'",
                        shell="powershell",
                        log_dir=".agents/logs/verify",
                    ),
                    self.repo_root,
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("日本語", output)

    def test_write_console_text_replaces_unencodable_characters(self) -> None:
        stream = io.TextIOWrapper(io.BytesIO(), encoding="cp932", errors="strict")
        with mock.patch.object(self.runner.sys, "stdout", stream):
            self.runner.write_console_text("ok\ufffd")
            stream.flush()
            stream.seek(0)
            written = stream.read()

        self.assertEqual(written, "ok?")
