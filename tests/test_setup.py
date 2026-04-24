from __future__ import annotations

import importlib.util
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "setup.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("setup_runner", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SetupRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner_module()
        temp_root = REPO_ROOT / "tmp" / "test-setup"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.case_root = temp_root / f"case-{uuid.uuid4().hex}"
        self.case_root.mkdir()
        self.claude_dir = self.case_root / ".claude"
        self.codex_dir = self.case_root / ".codex"

    def tearDown(self) -> None:
        shutil.rmtree(self.case_root, ignore_errors=True)

    def test_main_installs_python_assets_and_prunes_retired_files(self) -> None:
        stale_script = self.claude_dir / "scripts" / "retired.sh"
        stale_template = self.claude_dir / "templates" / "retired.txt"
        stale_skill = self.codex_dir / "skills" / "retired" / "SKILL.md"
        stale_script.parent.mkdir(parents=True, exist_ok=True)
        stale_template.parent.mkdir(parents=True, exist_ok=True)
        stale_skill.parent.mkdir(parents=True, exist_ok=True)
        stale_script.write_text("old\n", encoding="utf-8")
        stale_template.write_text("old\n", encoding="utf-8")
        stale_skill.write_text("old\n", encoding="utf-8")
        self.runner.write_manifest(
            self.claude_dir / "scripts" / self.runner.MANIFEST_NAME,
            {Path("retired.sh")},
        )
        self.runner.write_manifest(
            self.claude_dir / "templates" / self.runner.MANIFEST_NAME,
            {Path("retired.txt")},
        )
        self.runner.write_manifest(
            self.codex_dir / "skills" / self.runner.MANIFEST_NAME,
            {Path("retired/SKILL.md")},
        )

        exit_code = self.runner.main(
            [
                "--source-root",
                str(REPO_ROOT),
                "--claude-dir",
                str(self.claude_dir),
                "--codex-dir",
                str(self.codex_dir),
                "--codex",
                "-f",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.claude_dir / "scripts" / "setup.py").is_file())
        self.assertTrue((self.claude_dir / "scripts" / "init-project.py").is_file())
        self.assertTrue((self.codex_dir / "skills" / "init-project" / "SKILL.md").is_file())
        self.assertTrue((self.codex_dir / "skills" / "update-workflow" / "SKILL.md").is_file())
        # Deprecation stubs for old names must still ship so existing installs keep working.
        self.assertTrue((self.codex_dir / "skills" / "init-project-codex" / "SKILL.md").is_file())
        self.assertTrue((self.codex_dir / "skills" / "update-workflow-codex" / "SKILL.md").is_file())
        metadata = self.runner.read_json_file(self.claude_dir / self.runner.SOURCE_METADATA_NAME)
        self.assertEqual(metadata["source_root"], str(REPO_ROOT.resolve()))
        self.assertFalse(stale_script.exists())
        self.assertFalse(stale_template.exists())
        self.assertFalse(stale_skill.exists())
        self.assertFalse((self.claude_dir / "scripts" / "_legacy").exists())

    def test_main_preserves_unmanaged_user_assets(self) -> None:
        custom_command = self.claude_dir / "commands" / "custom.md"
        custom_skill = self.codex_dir / "skills" / "third-party" / "SKILL.md"
        custom_command.parent.mkdir(parents=True, exist_ok=True)
        custom_skill.parent.mkdir(parents=True, exist_ok=True)
        custom_command.write_text("keep\n", encoding="utf-8")
        custom_skill.write_text("keep\n", encoding="utf-8")
        self.runner.write_manifest(
            self.claude_dir / "commands" / self.runner.MANIFEST_NAME,
            {Path("init-project.md")},
        )
        self.runner.write_manifest(
            self.codex_dir / "skills" / self.runner.MANIFEST_NAME,
            {Path("init-project/SKILL.md")},
        )

        exit_code = self.runner.main(
            [
                "--source-root",
                str(REPO_ROOT),
                "--claude-dir",
                str(self.claude_dir),
                "--codex-dir",
                str(self.codex_dir),
                "--codex",
                "-f",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(custom_command.exists())
        self.assertTrue(custom_skill.exists())

    def test_main_force_preserves_pre_manifest_legacy_assets(self) -> None:
        legacy_script = self.claude_dir / "scripts" / "run-codex-plan-review.ps1"
        legacy_script.parent.mkdir(parents=True, exist_ok=True)
        legacy_script.write_text("legacy\n", encoding="utf-8")
        custom_script = self.claude_dir / "scripts" / "custom-tool.py"
        custom_script.write_text("keep\n", encoding="utf-8")

        exit_code = self.runner.main(
            [
                "--source-root",
                str(REPO_ROOT),
                "--claude-dir",
                str(self.claude_dir),
                "-f",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(legacy_script.exists())
        self.assertTrue(custom_script.exists())

    def test_main_force_preserves_unmanaged_colliding_file_at_managed_path(self) -> None:
        colliding = self.claude_dir / "commands" / "init-project.md"
        colliding.parent.mkdir(parents=True, exist_ok=True)
        colliding.write_text("custom-init\n", encoding="utf-8")

        exit_code = self.runner.main(
            [
                "--source-root",
                str(REPO_ROOT),
                "--claude-dir",
                str(self.claude_dir),
                "-f",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(colliding.read_text(encoding="utf-8"), "custom-init\n")
        manifest = self.runner.read_manifest(self.claude_dir / "commands" / self.runner.MANIFEST_NAME)
        self.assertNotIn(Path("init-project.md"), manifest)

    def test_main_without_force_preserves_existing_files(self) -> None:
        existing = self.claude_dir / "scripts" / "init-project.py"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("keep me\n", encoding="utf-8")

        exit_code = self.runner.main(
            [
                "--source-root",
                str(REPO_ROOT),
                "--claude-dir",
                str(self.claude_dir),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep me\n")

    def test_main_with_statusline_installs_statusline_and_updates_settings(self) -> None:
        exit_code = self.runner.main(
            [
                "--source-root",
                str(REPO_ROOT),
                "--claude-dir",
                str(self.claude_dir),
                "--statusline",
                "-f",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.claude_dir / "statusline.py").is_file())
        settings = self.runner.read_json_file(self.claude_dir / "settings.json")
        self.assertIn("statusLine", settings)
        command = settings["statusLine"]["command"]
        self.assertIn(str(self.claude_dir / "statusline.py"), command)
        self.assertIn(sys.executable, command)

    def test_resolve_repo_root_prefers_home_claude_dotfiles_when_installed(self) -> None:
        source_repo = self.case_root / "claude-dotfiles"
        for relative in ("commands", "templates", "scripts", "codex", "dotfiles"):
            (source_repo / relative).mkdir(parents=True, exist_ok=True)
        installed_root = self.case_root / ".claude"
        installed_root.mkdir(parents=True, exist_ok=True)

        with mock.patch.object(self.runner, "repo_root_from_script", return_value=installed_root), mock.patch.object(
            self.runner, "resolve_home_dir", return_value=self.case_root
        ):
            resolved = self.runner.resolve_repo_root(None, claude_dir=installed_root)

        self.assertEqual(resolved, source_repo.resolve())

    def test_resolve_repo_root_uses_metadata_when_installed(self) -> None:
        source_repo = self.case_root / "source-repo"
        for relative in ("commands", "templates", "scripts", "codex", "dotfiles"):
            (source_repo / relative).mkdir(parents=True, exist_ok=True)
        installed_root = self.case_root / ".claude"
        installed_root.mkdir(parents=True, exist_ok=True)
        self.runner.write_source_metadata(installed_root, source_repo)

        with mock.patch.object(self.runner, "repo_root_from_script", return_value=installed_root), mock.patch.object(
            self.runner, "resolve_home_dir", return_value=self.case_root / "missing-home"
        ):
            resolved = self.runner.resolve_repo_root(None, claude_dir=installed_root)

        self.assertEqual(resolved, source_repo.resolve())


if __name__ == "__main__":
    unittest.main()
