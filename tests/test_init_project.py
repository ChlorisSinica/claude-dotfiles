from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "init-project.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("init_project", SCRIPT_PATH)
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


class InitProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner_module()
        temp_root = REPO_ROOT / "tmp" / "test-init-project"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.repo_root = temp_root / f"case-{uuid.uuid4().hex}"
        self.repo_root.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def test_codex_main_scaffold_copies_python_runners_and_verify_config(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.repo_root / ".agents" / "AGENTS.md").is_file())
        self.assertTrue((self.repo_root / ".agents" / "context" / "plan.md").is_file())
        self.assertTrue((self.repo_root / ".agents" / "context" / "tasks.md").is_file())
        self.assertTrue((self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py").is_file())
        self.assertTrue((self.repo_root / ".agents" / "scripts" / "run-codex-impl-review.py").is_file())
        self.assertTrue((self.repo_root / ".agents" / "scripts" / "run-codex-impl-cycle.py").is_file())
        self.assertTrue((self.repo_root / ".agents" / "scripts" / "fix_codex_plugin_prompts.py").is_file())
        self.assertTrue((self.repo_root / ".claude" / "scripts" / "run-verify.py").is_file())
        self.assertTrue((self.repo_root / ".claude" / "scripts" / "verify-config.json").is_file())
        self.assertTrue((self.repo_root / ".claude" / "settings.json").is_file())
        self.assertTrue((self.repo_root / ".claude" / "settings.local.json").is_file())
        self.assertTrue((self.repo_root / ".claude" / "settings.local.json.bak").is_file())
        plan_review_skill = (self.repo_root / ".agents" / "skills" / "codex-plan-review" / "SKILL.md").read_text(encoding="utf-8")
        fkin_skill = (self.repo_root / ".agents" / "skills" / "codex-fkin-impl-cycle" / "SKILL.md").read_text(encoding="utf-8")
        agents_md = (self.repo_root / ".agents" / "AGENTS.md").read_text(encoding="utf-8")
        legacy_prompt = (self.repo_root / ".agents" / "prompts" / "codex_impl_review.md").read_text(encoding="utf-8")
        prompt_root = self.repo_root / ".agents" / "prompts" / "impl-review"
        expected_legacy_prompt = "\n\n".join(
            [
                (prompt_root / "core.md").read_text(encoding="utf-8").strip(),
                (prompt_root / "phases" / "quality.md").read_text(encoding="utf-8").strip(),
                (prompt_root / "preset.md").read_text(encoding="utf-8").strip(),
            ]
        ).rstrip() + "\n"
        self.assertIn("python3 .agents/scripts/run-codex-plan-review.py --phase arch", plan_review_skill)
        self.assertIn("python3 .agents/scripts/run-codex-impl-cycle.py", fkin_skill)
        self.assertIn("python3 .claude/scripts/run-verify.py", agents_md)
        self.assertIn("検証コマンド: `python3 -m pytest --tb=short -q`", agents_md)
        self.assertEqual(legacy_prompt, expected_legacy_prompt)
        gitignore = (self.repo_root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".agents/context/", gitignore)
        self.assertIn(".agents/reviews/", gitignore)
        self.assertIn(".agents/logs/", gitignore)
        self.assertIn(".agents/context/_codex_input.tmp", gitignore)
        self.assertNotIn(".agents/\n", gitignore)

        verify_config = json.loads((self.repo_root / ".claude" / "scripts" / "verify-config.json").read_text(encoding="utf-8"))
        expected_shell = "direct" if os.name == "nt" else "bash"
        self.assertEqual(verify_config["VERIFY_SHELL"], expected_shell)
        self.assertIn("pytest", verify_config["VERIFY_CMD"])
        self.assertTrue(verify_config["VERIFY_CMD"].startswith("python3 "))
        self.assertEqual(verify_config["PRIMARY_LOG_DIR"], ".agents/logs/verify")

    def test_manifest_roundtrip_with_preset_and_template(self) -> None:
        manifest_path = self.repo_root / "manifest.json"

        self.runner.write_workflow_manifest(
            manifest_path,
            {"skills/codex-plan/SKILL.md", "AGENTS.md"},
            preset="python",
            template="codex-main",
        )

        manifest = self.runner.read_workflow_manifest_data(manifest_path)
        self.assertEqual(manifest.managed, {"skills/codex-plan/SKILL.md", "AGENTS.md"})
        self.assertEqual(manifest.preset, "python")
        self.assertEqual(manifest.template, "codex-main")

    def test_manifest_read_legacy_schema_without_preset(self) -> None:
        manifest_path = self.repo_root / "legacy-manifest.json"
        manifest_path.write_text(
            json.dumps({"managed": ["commands/plan.md"]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        manifest = self.runner.read_workflow_manifest_data(manifest_path)
        self.assertEqual(manifest.managed, {"commands/plan.md"})
        self.assertIsNone(manifest.preset)
        self.assertIsNone(manifest.template)

    def test_codex_main_claude_manifest_tagged_with_codex_main_template(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])

        self.assertEqual(exit_code, 0)

        agents_manifest = json.loads(
            (self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        claude_manifest = json.loads(
            (self.repo_root / ".claude" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        agents_scripts_manifest = json.loads(
            (self.repo_root / ".agents" / "scripts" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        claude_scripts_manifest = json.loads(
            (self.repo_root / ".claude" / "scripts" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )

        for manifest in (agents_manifest, claude_manifest, agents_scripts_manifest, claude_scripts_manifest):
            self.assertEqual(manifest["preset"], "python")
            self.assertEqual(manifest["template"], "codex-main")

    def test_windows_bash_chain_preset_materializes_to_powershell(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows-only materialization behavior")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python-pytorch"])

        self.assertEqual(exit_code, 0)
        verify_config = json.loads((self.repo_root / ".claude" / "scripts" / "verify-config.json").read_text(encoding="utf-8"))
        self.assertEqual(verify_config["VERIFY_SHELL"], "powershell")
        self.assertIn("if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }", verify_config["VERIFY_CMD"])
        self.assertTrue(verify_config["VERIFY_CMD"].startswith("python3 "))

    def test_workflow_only_preserves_context_and_reviews(self) -> None:
        # Scaffold first so smart-mode detects the manifest and routes to update.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                scaffold_exit = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(scaffold_exit, 0)

        agents_context = self.repo_root / ".agents" / "context"
        agents_reviews = self.repo_root / ".agents" / "reviews"
        (agents_context / "plan.md").write_text("keep me\n", encoding="utf-8")
        (agents_reviews / "sessions.json").write_text('{"keep": true}\n', encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--update"])

        self.assertEqual(exit_code, 0)
        self.assertEqual((agents_context / "plan.md").read_text(encoding="utf-8"), "keep me\n")
        self.assertEqual((agents_reviews / "sessions.json").read_text(encoding="utf-8"), '{"keep": true}\n')
        gitignore = (self.repo_root / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn(".agents/\n", gitignore)
        self.assertIn(".agents/context/", gitignore)

    def test_codex_main_workflow_only_keeps_preserved_manifest_entries(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])

        self.assertEqual(exit_code, 0)

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                refresh_exit = self.runner.main(["-t", "codex-main", "python", "--update"])

        self.assertEqual(refresh_exit, 0)
        manifest = json.loads((self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertIn("context/.gitkeep", manifest["managed"])
        self.assertIn("reviews/.gitkeep", manifest["managed"])
        self.assertIn("reviews/sessions.json", manifest["managed"])

    def test_codex_main_force_preserves_existing_context_files(self) -> None:
        agents_context = self.repo_root / ".agents" / "context"
        agents_context.mkdir(parents=True, exist_ok=True)
        (agents_context / "plan.md").write_text("keep plan\n", encoding="utf-8")
        (agents_context / "tasks.md").write_text("keep tasks\n", encoding="utf-8")
        (agents_context / "implementation_gap_audit.md").write_text("keep gap\n", encoding="utf-8")
        (agents_context / "research.md").write_text("keep research\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        self.assertEqual((agents_context / "plan.md").read_text(encoding="utf-8"), "keep plan\n")
        self.assertEqual((agents_context / "tasks.md").read_text(encoding="utf-8"), "keep tasks\n")
        self.assertEqual((agents_context / "implementation_gap_audit.md").read_text(encoding="utf-8"), "keep gap\n")
        self.assertEqual((agents_context / "research.md").read_text(encoding="utf-8"), "keep research\n")

    def test_codex_main_workflow_only_does_not_recreate_missing_context_seeds(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])

        self.assertEqual(exit_code, 0)
        agents_context = self.repo_root / ".agents" / "context"
        for name in ("research.md", "plan.md", "tasks.md", "implementation_gap_audit.md"):
            (agents_context / name).unlink()

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                refresh_exit = self.runner.main(["-t", "codex-main", "python", "--update"])

        self.assertEqual(refresh_exit, 0)
        for name in ("research.md", "plan.md", "tasks.md", "implementation_gap_audit.md"):
            self.assertFalse((agents_context / name).exists(), name)

    def test_bare_preset_defaults_to_project_init_template(self) -> None:
        # Help text advertises "-t project-init (default)" — verify the default actually applies.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["python"])

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.repo_root / ".claude" / "commands" / "plan.md").is_file())
        self.assertFalse((self.repo_root / ".agents").exists())

    def test_bare_survey_preset_infers_research_survey_template(self) -> None:
        # `survey-*` presets only live in research-survey; without inference, bare invocation
        # would fall into project-init and fail with "Unknown preset".
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["survey-cv"])

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.repo_root / ".claude" / "CLAUDE.md").is_file())

    def test_project_init_template_copies_claude_assets(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "project-init", "python"])

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.repo_root / ".claude" / "commands" / "plan.md").is_file())
        self.assertTrue((self.repo_root / ".claude" / "agents" / "master_workflow.md").is_file())
        self.assertTrue((self.repo_root / ".claude" / "scripts" / "run-verify.py").is_file())
        self.assertTrue((self.repo_root / ".claude" / "scripts" / "verify-config.json").is_file())
        self.assertTrue((self.repo_root / ".claude" / "settings.json").is_file())
        self.assertTrue((self.repo_root / ".claude" / "settings.local.json.bak").is_file())
        self.assertTrue((self.repo_root / ".claude" / "hooks" / "syntax-check.py").is_file())
        self.assertTrue((self.repo_root / ".claude" / "CLAUDE.md").is_file())
        self.assertFalse((self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py").exists())
        implement_md = (self.repo_root / ".claude" / "commands" / "implement.md").read_text(encoding="utf-8")
        master_workflow = (self.repo_root / ".claude" / "agents" / "master_workflow.md").read_text(encoding="utf-8")
        settings = json.loads((self.repo_root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        local_settings = json.loads((self.repo_root / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        syntax_hook = (self.repo_root / ".claude" / "hooks" / "syntax-check.py").read_text(encoding="utf-8")
        verify_config = json.loads((self.repo_root / ".claude" / "scripts" / "verify-config.json").read_text(encoding="utf-8"))
        self.assertIn("python3 .claude/scripts/run-verify.py", implement_md)
        self.assertIn("python3 -m pytest --tb=short -q", master_workflow)
        self.assertEqual(
            settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"],
            "python3 .claude/hooks/syntax-check.py",
        )
        self.assertIn('SYNTAX_CMD = "python3 -m py_compile \\"$FILE\\""', syntax_hook)
        self.assertIn("import shlex", syntax_hook)
        self.assertIn('FILE_PLACEHOLDER = "$FILE"', syntax_hook)
        self.assertIn("subprocess.run(build_command(file_path), capture_output=True, text=True)", syntax_hook)
        self.assertNotIn("shell=True", syntax_hook)
        self.assertTrue((self.repo_root / ".claude" / "settings.local.json").is_file())
        self.assertIn(
            "Bash(python3 .claude/hooks/syntax-check.py:*)",
            local_settings["permissions"]["allow"],
        )
        self.assertIn("検証コマンド: `python3 -m pytest --tb=short -q`", (self.repo_root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertEqual(verify_config["PRIMARY_LOG_DIR"], ".claude/logs/verify")
        gitignore = (self.repo_root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".claude/context/", gitignore)
        self.assertIn("__pycache__/", gitignore)
        self.assertIn(".claude/logs/verify/", gitignore)

    def test_project_init_workflow_only_preserves_context(self) -> None:
        # Scaffold first so smart-mode detects the manifest and routes to update.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                scaffold_exit = self.runner.main(["-t", "project-init", "python"])
        self.assertEqual(scaffold_exit, 0)

        claude_context = self.repo_root / ".claude" / "context"
        claude_context.mkdir(parents=True, exist_ok=True)
        (claude_context / "notes.md").write_text("keep me\n", encoding="utf-8")
        (claude_context / "failure_report.md").write_text("keep failure\n", encoding="utf-8")
        agents_dir = self.repo_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "sessions.json").write_text('{"keep": true}\n', encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "project-init", "python", "--update"])

        self.assertEqual(exit_code, 0)
        self.assertEqual((claude_context / "notes.md").read_text(encoding="utf-8"), "keep me\n")
        self.assertEqual((claude_context / "failure_report.md").read_text(encoding="utf-8"), "keep failure\n")
        self.assertEqual((agents_dir / "sessions.json").read_text(encoding="utf-8"), '{"keep": true}\n')

    def test_project_init_workflow_only_keeps_preserved_manifest_entries(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "project-init", "python"])

        self.assertEqual(exit_code, 0)

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                refresh_exit = self.runner.main(["-t", "project-init", "python", "--update"])

        self.assertEqual(refresh_exit, 0)
        manifest = json.loads((self.repo_root / ".claude" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertIn("context/.gitkeep", manifest["managed"])
        self.assertIn("agents/sessions.json", manifest["managed"])

    def test_project_init_force_preserves_existing_failure_report(self) -> None:
        claude_context = self.repo_root / ".claude" / "context"
        claude_context.mkdir(parents=True, exist_ok=True)
        failure_report = claude_context / "failure_report.md"
        failure_report.write_text("keep failure\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "project-init", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(failure_report.read_text(encoding="utf-8"), "keep failure\n")

    def test_codex_main_update_merges_managed_active_settings_local_entries(self) -> None:
        # Scaffold first, then add a user-owned entry to the managed settings.local.json,
        # and verify --update merges user additions with refreshed managed defaults.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main(["-t", "codex-main", "python"]), 0)

        active = self.repo_root / ".claude" / "settings.local.json"
        data = json.loads(active.read_text(encoding="utf-8"))
        data["permissions"]["allow"].append("Bash(custom-local:*)")
        active.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["--update"])

        self.assertEqual(exit_code, 0)
        merged = json.loads(active.read_text(encoding="utf-8"))
        allow = merged["permissions"]["allow"]
        self.assertIn("Bash(custom-local:*)", allow)
        self.assertIn("Bash(python .claude/scripts/run-verify.py:*)", allow)
        self.assertIn("Bash(git status:*)", allow)

    def test_codex_main_fresh_overwrites_unmanaged_claude_settings_files(self) -> None:
        # --fresh is the nuclear option: unmanaged settings files get overwritten.
        claude_dir = self.repo_root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_bak = claude_dir / "settings.local.json.bak"
        settings_active = claude_dir / "settings.local.json"
        settings_path.write_text('{"hooks":{"SessionStart":[]}}\n', encoding="utf-8")
        settings_bak.write_text('{"permissions":{"allow":["Bash(custom-bak:*)"]}}\n', encoding="utf-8")
        settings_active.write_text('{"permissions":{"allow":["Bash(custom-active:*)"]}}\n', encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        # User's pre-existing content replaced with the template's generated content.
        self.assertNotEqual(settings_path.read_text(encoding="utf-8"), '{"hooks":{"SessionStart":[]}}\n')
        self.assertNotEqual(settings_bak.read_text(encoding="utf-8"), '{"permissions":{"allow":["Bash(custom-bak:*)"]}}\n')
        self.assertNotEqual(settings_active.read_text(encoding="utf-8"), '{"permissions":{"allow":["Bash(custom-active:*)"]}}\n')

    def test_codex_main_force_drops_stale_standard_template_claude_manifest_entries(self) -> None:
        claude_dir = self.repo_root / ".claude"
        hooks_dir = claude_dir / "hooks"
        claude_dir.mkdir(parents=True, exist_ok=True)
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "CLAUDE.md").write_text("legacy\n", encoding="utf-8")
        (hooks_dir / "syntax-check.py").write_text("legacy\n", encoding="utf-8")
        (claude_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["CLAUDE.md", "hooks/syntax-check.py", "settings.local.json"]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        manifest = json.loads((claude_dir / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertNotIn("CLAUDE.md", manifest["managed"])
        self.assertNotIn("hooks/syntax-check.py", manifest["managed"])
        self.assertFalse((claude_dir / "CLAUDE.md").exists())
        self.assertFalse((hooks_dir / "syntax-check.py").exists())

    def test_discover_portable_python_launcher_probes_candidates(self) -> None:
        launcher_candidates: list[tuple[str, ...]] = []

        def fake_which(name: str) -> str | None:
            return name

        def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            candidate = tuple(cmd[:-2])
            launcher_candidates.append(candidate)
            stdout = {
                ("py", "-3"): "3.10\n",
                ("python3",): "3.11\n",
                ("python",): "3.12\n",
            }.get(candidate, "")
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

        with mock.patch.object(self.runner.shutil, "which", side_effect=fake_which):
            with mock.patch.object(self.runner.subprocess, "run", side_effect=fake_run):
                launcher = self.runner.discover_portable_python_launcher()

        if os.name == "nt":
            self.assertEqual(launcher, "python3")
            self.assertEqual(launcher_candidates[:2], [("py", "-3"), ("python3",)])
        else:
            self.assertEqual(launcher, "python3")
            self.assertEqual(launcher_candidates[:1], [("python3",)])

    def test_codex_main_workflow_only_force_prunes_retired_shell_runners(self) -> None:
        # Scaffold first so smart-mode detects the manifest and routes to update.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                scaffold_exit = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(scaffold_exit, 0)

        agents_scripts = self.repo_root / ".agents" / "scripts"
        claude_scripts = self.repo_root / ".claude" / "scripts"
        retired_agents = [
            agents_scripts / "run-codex-plan-review.ps1",
            agents_scripts / "run-codex-impl-review.ps1",
        ]
        retired_claude = [
            claude_scripts / "run-verify.sh",
            claude_scripts / "run-verify.ps1",
        ]
        for path in retired_agents + retired_claude:
            path.write_text("legacy\n", encoding="utf-8")
        # Seed retired entries into each scripts manifest so pruning can find them.
        for scripts_dir, retired in ((agents_scripts, retired_agents), (claude_scripts, retired_claude)):
            manifest_path = scripts_dir / self.runner.WORKFLOW_MANIFEST_NAME
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            existing["managed"] = sorted(set(existing.get("managed", [])) | {path.name for path in retired})
            manifest_path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--update"])

        self.assertEqual(exit_code, 0)
        for path in retired_agents + retired_claude:
            self.assertFalse(path.exists(), str(path))

    def test_codex_main_force_prunes_retired_shell_runners_without_workflow_only(self) -> None:
        # Pre-seed retired files at the legacy scripts/ path with a legacy manifest.
        # The migration step in initialize_codex_main must clear them out wholesale.
        scripts_dir = self.repo_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        retired = [
            scripts_dir / "run-codex-plan-review.ps1",
            scripts_dir / "run-codex-impl-review.ps1",
            scripts_dir / "run-verify.sh",
            scripts_dir / "run-verify.ps1",
        ]
        for path in retired:
            path.write_text("legacy\n", encoding="utf-8")
        manifest = self.repo_root / "scripts" / self.runner.WORKFLOW_MANIFEST_NAME
        manifest.write_text(
            json.dumps(
                {
                    "managed": [path.name for path in retired],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        for path in retired:
            self.assertFalse(path.exists(), str(path))
        # Legacy manifest is removed by migration.
        self.assertFalse(manifest.exists())

    def test_codex_main_force_prunes_removed_workflow_assets_tracked_by_manifest(self) -> None:
        stale_skill = self.repo_root / ".agents" / "skills" / "removed-skill" / "SKILL.md"
        stale_prompt = self.repo_root / ".agents" / "prompts" / "removed.md"
        stale_skill.parent.mkdir(parents=True, exist_ok=True)
        stale_prompt.parent.mkdir(parents=True, exist_ok=True)
        stale_skill.write_text("legacy\n", encoding="utf-8")
        stale_prompt.write_text("legacy\n", encoding="utf-8")
        manifest = self.repo_root / ".agents" / ".claude-dotfiles-managed.json"
        manifest.write_text(
            json.dumps(
                {
                    "managed": [
                        "skills/removed-skill/SKILL.md",
                        "prompts/removed.md",
                    ]
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--update"])

        self.assertEqual(exit_code, 0)
        self.assertFalse(stale_skill.exists())
        self.assertFalse(stale_prompt.exists())

    def test_codex_main_fails_on_malformed_workflow_manifest(self) -> None:
        manifest = self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("{not json\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--update"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(manifest.read_text(encoding="utf-8"), "{not json\n")

    def test_codex_main_force_preserves_untracked_custom_workflow_assets_without_manifest(self) -> None:
        # No manifest; this case goes through --fresh (which initializes a new scaffold
        # and leaves non-managed user files untouched).
        custom_skill = self.repo_root / ".agents" / "skills" / "custom-skill" / "SKILL.md"
        custom_prompt = self.repo_root / ".agents" / "prompts" / "custom.md"
        custom_skill.parent.mkdir(parents=True, exist_ok=True)
        custom_prompt.parent.mkdir(parents=True, exist_ok=True)
        custom_skill.write_text("custom\n", encoding="utf-8")
        custom_prompt.write_text("custom\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(custom_skill.exists())
        self.assertTrue(custom_prompt.exists())

    def test_codex_main_fresh_overwrites_unmanaged_colliding_workflow_file(self) -> None:
        # --fresh is the nuclear option: it overwrites files at template paths even
        # when the manifest does not record them as managed. Users who want to keep
        # the pre-existing file must back it up before running --fresh.
        custom_agents = self.repo_root / ".agents" / "AGENTS.md"
        custom_agents.parent.mkdir(parents=True, exist_ok=True)
        custom_agents.write_text("custom agents\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        # --fresh wrote the template version on top of the user's custom AGENTS.md.
        self.assertNotEqual(custom_agents.read_text(encoding="utf-8"), "custom agents\n")
        manifest = json.loads((self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertIn("AGENTS.md", manifest["managed"])

    def test_codex_main_force_preserves_untracked_custom_runner_names_without_manifest(self) -> None:
        # User-owned file at the legacy scripts/ path with NO legacy manifest must
        # not be touched: migration only acts when a manifest declares ownership.
        custom_runner = self.repo_root / "scripts" / "run-verify.sh"
        custom_runner.parent.mkdir(parents=True, exist_ok=True)
        custom_runner.write_text("custom\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(custom_runner.exists())
        self.assertEqual(custom_runner.read_text(encoding="utf-8"), "custom\n")

    def test_codex_main_fresh_overwrites_unmanaged_colliding_runner_file(self) -> None:
        # --fresh is the nuclear option: even a user-owned runner at a template path gets overwritten.
        custom_runner = self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py"
        custom_runner.parent.mkdir(parents=True, exist_ok=True)
        custom_runner.write_text("custom runner\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        self.assertNotEqual(custom_runner.read_text(encoding="utf-8"), "custom runner\n")
        manifest = json.loads(
            (self.repo_root / ".agents" / "scripts" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertIn("run-codex-plan-review.py", manifest["managed"])

    def test_codex_main_non_force_keeps_retired_runner_manifest_until_force(self) -> None:
        # Seed retired files at the new locations with their respective manifests.
        agents_scripts = self.repo_root / ".agents" / "scripts"
        claude_scripts = self.repo_root / ".claude" / "scripts"
        agents_scripts.mkdir(parents=True, exist_ok=True)
        claude_scripts.mkdir(parents=True, exist_ok=True)
        retired_agents = [
            agents_scripts / "run-codex-plan-review.ps1",
            agents_scripts / "run-codex-impl-review.ps1",
        ]
        retired_claude = [
            claude_scripts / "run-verify.sh",
            claude_scripts / "run-verify.ps1",
        ]
        for path in retired_agents + retired_claude:
            path.write_text("legacy\n", encoding="utf-8")
        for scripts_dir, retired in ((agents_scripts, retired_agents), (claude_scripts, retired_claude)):
            (scripts_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
                json.dumps({"managed": [path.name for path in retired]}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                non_force_exit = self.runner.main(["-t", "codex-main", "python"])

        self.assertEqual(non_force_exit, 0)
        for path in retired_agents + retired_claude:
            self.assertTrue(path.exists(), str(path))

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                force_exit = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(force_exit, 0)
        for path in retired_agents + retired_claude:
            self.assertFalse(path.exists(), str(path))

    def test_codex_main_fresh_recovers_from_malformed_active_settings_local(self) -> None:
        # --fresh is the recovery path: it must clean-overwrite a malformed
        # managed settings.local.json instead of choking on the merge step.
        claude_dir = self.repo_root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        active = claude_dir / "settings.local.json"
        active.write_text("{bad json\n", encoding="utf-8")
        (claude_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "managed": ["settings.local.json"],
                    "template": "codex-main",
                    "preset": "python",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        # The malformed content is replaced with a valid JSON template.
        self.assertNotEqual(active.read_text(encoding="utf-8"), "{bad json\n")
        parsed = json.loads(active.read_text(encoding="utf-8"))
        self.assertIn("permissions", parsed)

    def test_project_init_fresh_overwrites_unmanaged_claude_settings_files(self) -> None:
        # --fresh overwrites user-owned settings even in the standard template.
        claude_dir = self.repo_root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_bak = claude_dir / "settings.local.json.bak"
        settings_active = claude_dir / "settings.local.json"
        settings_path.write_text('{"hooks":{"SessionStart":[]}}\n', encoding="utf-8")
        settings_bak.write_text('{"permissions":{"allow":["Bash(custom-bak:*)"]}}\n', encoding="utf-8")
        settings_active.write_text('{"permissions":{"allow":["Bash(custom-active:*)"]}}\n', encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "project-init", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        self.assertNotEqual(settings_path.read_text(encoding="utf-8"), '{"hooks":{"SessionStart":[]}}\n')
        self.assertNotEqual(settings_bak.read_text(encoding="utf-8"), '{"permissions":{"allow":["Bash(custom-bak:*)"]}}\n')
        self.assertNotEqual(settings_active.read_text(encoding="utf-8"), '{"permissions":{"allow":["Bash(custom-active:*)"]}}\n')

    def test_project_init_force_drops_stale_codex_runner_manifest_entries(self) -> None:
        # Seed stale codex runners at the new agents/scripts/ location with their manifest.
        # project-init template has no concept of agents-side runners, so they must be
        # pruned out entirely.
        agents_scripts = self.repo_root / ".agents" / "scripts"
        claude_scripts = self.repo_root / ".claude" / "scripts"
        agents_scripts.mkdir(parents=True, exist_ok=True)
        claude_scripts.mkdir(parents=True, exist_ok=True)
        stale = [
            claude_scripts / "run-codex-plan-review.py",
            claude_scripts / "run-codex-impl-review.py",
            claude_scripts / "run-codex-impl-cycle.py",
        ]
        for path in stale:
            path.write_text("legacy\n", encoding="utf-8")
        manifest = claude_scripts / self.runner.WORKFLOW_MANIFEST_NAME
        manifest.write_text(
            json.dumps({"managed": [path.name for path in stale]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "project-init", "python", "--fresh"])

        self.assertEqual(exit_code, 0)
        updated = json.loads(manifest.read_text(encoding="utf-8"))
        for path in stale:
            self.assertNotIn(path.name, updated["managed"])
            self.assertFalse(path.exists(), str(path))

    # ===== T6: smart mode / manifest tag / preset mismatch / cross-template =====

    def test_smart_update_uses_manifest_preset_when_arg_omitted(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main(["-t", "codex-main", "python"]), 0)
                # Bare invocation after scaffold → smart update, preset recovered from manifest
                self.assertEqual(self.runner.main([]), 0)

        manifest = json.loads(
            (self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["preset"], "python")
        self.assertEqual(manifest["template"], "codex-main")

    def test_update_mode_preset_mismatch_returns_exit_code_3(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main(["-t", "codex-main", "python"]), 0)
                # Different preset + no --accept-preset-change → exit 3
                self.assertEqual(self.runner.main(["python-pytorch"]), 3)

        # Manifest preset unchanged
        manifest = json.loads(
            (self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["preset"], "python")

    def test_preset_mismatch_with_accept_flag_succeeds(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main(["-t", "codex-main", "python"]), 0)
                self.assertEqual(
                    self.runner.main(["python-pytorch", "--accept-preset-change"]), 0
                )

        manifest = json.loads(
            (self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["preset"], "python-pytorch")

    def test_update_flag_errors_without_manifest(self) -> None:
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--update"])
        self.assertEqual(exit_code, 1)

    def test_cross_template_switch_is_blocked(self) -> None:
        # Scaffold as project-init, then try to switch to codex-main via -t → error
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main(["-t", "project-init", "python"]), 0)
                exit_code = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(exit_code, 1)

    def test_legacy_manifest_infers_codex_main_from_managed_paths(self) -> None:
        # Simulate pre-Bundle-2 codex-main manifest (no template/preset fields)
        agents_manifest = self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME
        agents_manifest.parent.mkdir(parents=True, exist_ok=True)
        agents_manifest.write_text(
            json.dumps({"managed": ["skills/codex-plan/SKILL.md", "AGENTS.md"]}) + "\n",
            encoding="utf-8",
        )

        active_template, manifest_preset, uninferable = self.runner.detect_active_template(self.repo_root)
        self.assertEqual(active_template, "codex-main")
        self.assertIsNone(manifest_preset)
        self.assertFalse(uninferable)

    def test_legacy_manifest_uninferable_when_paths_ambiguous(self) -> None:
        claude_manifest = self.repo_root / ".claude" / self.runner.WORKFLOW_MANIFEST_NAME
        claude_manifest.parent.mkdir(parents=True, exist_ok=True)
        # managed entries don't match any template's distinguishing paths
        claude_manifest.write_text(
            json.dumps({"managed": ["unknown/file.md"]}) + "\n",
            encoding="utf-8",
        )

        active_template, _, uninferable = self.runner.detect_active_template(self.repo_root)
        self.assertIsNone(active_template)
        self.assertTrue(uninferable)

        # CLI requires explicit -t in this case
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["python"])
        self.assertEqual(exit_code, 1)

    def test_detect_active_template_no_manifest(self) -> None:
        active_template, manifest_preset, uninferable = self.runner.detect_active_template(self.repo_root)
        self.assertIsNone(active_template)
        self.assertIsNone(manifest_preset)
        self.assertFalse(uninferable)

    def test_fresh_mode_overrides_existing_manifest_and_overwrites_unmanaged(self) -> None:
        # --fresh ignores any existing manifest and overwrites non-managed files at template paths.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main(["-t", "codex-main", "python"]), 0)

        # User directly edits a managed file AND adds an unmanaged file at a template path.
        agents_md = self.repo_root / ".agents" / "AGENTS.md"
        agents_md.write_text("user tampered\n", encoding="utf-8")
        # Remove manifest entry so AGENTS.md is treated as unmanaged.
        manifest_path = self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_data["managed"] = [p for p in manifest_data["managed"] if p != "AGENTS.md"]
        manifest_path.write_text(json.dumps(manifest_data) + "\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])
        self.assertEqual(exit_code, 0)
        # --fresh overwrote the unmanaged AGENTS.md back to template content.
        self.assertNotEqual(agents_md.read_text(encoding="utf-8"), "user tampered\n")

    def test_codex_main_repo_bare_init_does_not_touch_standard_claude_dirs(self) -> None:
        # .claude/manifest.template == "codex-main" is authoritative — smart mode must NOT
        # scaffold standard-template .claude/commands/ on a codex-main repo.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main(["-t", "codex-main", "python"]), 0)

        # Bare invocation after codex-main scaffold → smart update on codex-main, not project-init.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                self.assertEqual(self.runner.main([]), 0)

        # The codex-main refresh must not have created standard-template artifacts like
        # .claude/commands/plan.md (which only the project-init template owns).
        self.assertFalse((self.repo_root / ".claude" / "commands").exists())
        self.assertFalse((self.repo_root / ".claude" / "agents").exists())
        # Confirm the manifest still records codex-main as the active template.
        claude_manifest = json.loads(
            (self.repo_root / ".claude" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertEqual(claude_manifest["template"], "codex-main")

    def test_stale_agents_manifest_after_template_switch_is_ignored(self) -> None:
        # Simulate the post-switch state: .claude/manifest.template = "project-init"
        # is authoritative; a stale .agents/manifest (leftover from an earlier codex-main)
        # must NOT cause the smart router to treat this as codex-main or to raise a
        # cross-template error.
        agents_manifest = self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME
        agents_manifest.parent.mkdir(parents=True, exist_ok=True)
        agents_manifest.write_text(
            json.dumps({"managed": ["skills/codex-plan/SKILL.md"], "template": "codex-main", "preset": "python"}) + "\n",
            encoding="utf-8",
        )
        claude_manifest = self.repo_root / ".claude" / self.runner.WORKFLOW_MANIFEST_NAME
        claude_manifest.parent.mkdir(parents=True, exist_ok=True)
        claude_manifest.write_text(
            json.dumps({"managed": ["commands/plan.md"], "template": "project-init", "preset": "python"}) + "\n",
            encoding="utf-8",
        )

        # detect_active_template should report project-init (authoritative .claude manifest).
        active_template, manifest_preset, _ = self.runner.detect_active_template(self.repo_root)
        self.assertEqual(active_template, "project-init")
        self.assertEqual(manifest_preset, "python")

        # Bare invocation should route to project-init update, not cross-template error.
        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main([])
        self.assertEqual(exit_code, 0)

    def test_legacy_scripts_layout_migrates_to_split_layout(self) -> None:
        # Pre-(C) layout: every runner lived under scripts/ with a single manifest.
        # An update on such a repo must remove the legacy files + manifest and
        # populate .agents/scripts/ and .claude/scripts/ with fresh copies.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        legacy_files = [
            "run-codex-plan-review.py",
            "run-codex-impl-review.py",
            "run-codex-impl-cycle.py",
            "fix_codex_plugin_prompts.py",
            "run-verify.py",
            "verify-config.json",
        ]
        for name in legacy_files:
            (legacy_scripts / name).write_text("legacy\n", encoding="utf-8")
        # Also drop a user-owned file that the manifest does NOT list — must survive.
        user_file = legacy_scripts / "user-owned.txt"
        user_file.write_text("user\n", encoding="utf-8")
        legacy_manifest = legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME
        legacy_manifest.write_text(
            json.dumps(
                {
                    "managed": legacy_files,
                    "preset": "python",
                    "template": "codex-main",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Seed the .agents/.claude-dotfiles-managed.json to make smart-mode pick codex-main.
        agents_dir = self.repo_root / ".agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "managed": ["AGENTS.md", "skills/codex-plan/SKILL.md"],
                    "preset": "python",
                    "template": "codex-main",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main([])

        self.assertEqual(exit_code, 0)
        # All legacy managed files removed, manifest gone, but user file preserved.
        for name in legacy_files:
            self.assertFalse((legacy_scripts / name).exists(), name)
        self.assertFalse(legacy_manifest.exists())
        self.assertTrue(user_file.exists())
        self.assertEqual(user_file.read_text(encoding="utf-8"), "user\n")
        # New layout populated.
        self.assertTrue((self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py").is_file())
        self.assertTrue((self.repo_root / ".claude" / "scripts" / "run-verify.py").is_file())
        self.assertTrue((self.repo_root / ".claude" / "scripts" / "verify-config.json").is_file())

    def test_legacy_scripts_migration_preserves_verify_config_customizations(self) -> None:
        # P1-3 regression guard: a pre-(C) verify-config.json with user overrides
        # must survive a normal update (the value is carried forward to the new
        # location and write_verify_config preserves it as user-owned).
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        custom_config = {
            "VERIFY_CMD": "echo custom-verify",
            "VERIFY_SHELL": "direct",
            "PRIMARY_LOG_DIR": "custom/log/dir",
        }
        (legacy_scripts / "verify-config.json").write_text(
            json.dumps(custom_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for name in ("run-verify.py", "run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py", "fix_codex_plugin_prompts.py"):
            (legacy_scripts / name).write_text("legacy\n", encoding="utf-8")
        (legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "managed": [
                        "verify-config.json",
                        "run-verify.py",
                        "run-codex-plan-review.py",
                        "run-codex-impl-review.py",
                        "run-codex-impl-cycle.py",
                        "fix_codex_plugin_prompts.py",
                    ],
                    "preset": "python",
                    "template": "codex-main",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Seed both .agents/ and .claude/ manifests so smart-mode picks codex-main.
        agents_dir = self.repo_root / ".agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["AGENTS.md", "skills/codex-plan/SKILL.md"], "preset": "python", "template": "codex-main"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main([])
        self.assertEqual(exit_code, 0)

        new_config_path = self.repo_root / ".claude" / "scripts" / "verify-config.json"
        self.assertTrue(new_config_path.is_file())
        new_config = json.loads(new_config_path.read_text(encoding="utf-8"))
        self.assertEqual(new_config, custom_config)
        # Carried-forward file is tracked as managed in the new manifest, so
        # future updates treat it consistently with any other managed file.
        new_manifest = json.loads(
            (self.repo_root / ".claude" / "scripts" / self.runner.WORKFLOW_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertIn("verify-config.json", new_manifest["managed"])

    def test_legacy_scripts_migration_skipped_on_dotfiles_source_repo(self) -> None:
        # P1-2 regression guard: when init-project runs on the dotfiles source
        # repo itself, scripts/ contains the master runners that other repos
        # bundle. Migration must skip so it never deletes those masters.
        with mock.patch.object(self.runner, "repo_root_from_script", return_value=self.repo_root):
            self.assertTrue(self.runner.is_dotfiles_source_repo(self.repo_root))
            # Even with a legacy manifest sitting in scripts/, neither phase
            # should touch the master files.
            scripts_dir = self.repo_root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "run-verify.py").write_text("master\n", encoding="utf-8")
            (scripts_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
                json.dumps({"managed": ["run-verify.py"]}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.runner.migrate_legacy_scripts_carry_forward(self.repo_root)
            self.runner.migrate_legacy_scripts_cleanup(
                self.repo_root,
                new_scripts_present={"run-verify.py"},
                template_runner_names={"run-verify.py"},
            )
        self.assertTrue((scripts_dir / "run-verify.py").is_file())
        self.assertEqual((scripts_dir / "run-verify.py").read_text(encoding="utf-8"), "master\n")
        self.assertTrue((scripts_dir / self.runner.WORKFLOW_MANIFEST_NAME).is_file())

    def test_legacy_scripts_migration_atomic_on_collision(self) -> None:
        # P1-1 regression guard: if a fresh-init mode (no manifest) runs on a
        # repo that has both a legacy scripts/ layout AND an unmanaged file at
        # one of the new destinations, init must abort BEFORE deleting the
        # legacy state.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        (legacy_scripts / "run-verify.py").write_text("legacy verify\n", encoding="utf-8")
        legacy_manifest = legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME
        legacy_manifest.write_text(
            json.dumps({"managed": ["run-verify.py"]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        # Plant an unmanaged collision at the new destination so non-force init fails.
        new_runner = self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py"
        new_runner.parent.mkdir(parents=True, exist_ok=True)
        new_runner.write_text("user owned\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(exit_code, 1)
        # Legacy scripts/ files and manifest preserved — operation was atomic.
        self.assertTrue((legacy_scripts / "run-verify.py").is_file())
        self.assertTrue(legacy_manifest.is_file())
        # User-owned collision file untouched.
        self.assertEqual(new_runner.read_text(encoding="utf-8"), "user owned\n")

    def test_legacy_scripts_cleanup_keeps_unmigrated_entries(self) -> None:
        # Regression for the "cleanup deletes everything in the legacy manifest"
        # bug: in update mode, copy_runner_files_to silently skips a
        # destination that already contains an unmanaged user file. The legacy
        # copy must NOT be deleted in that case, otherwise the user loses both
        # the old managed file and any working content.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        for name in ("run-verify.py", "run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py", "fix_codex_plugin_prompts.py"):
            (legacy_scripts / name).write_text(f"legacy-{name}\n", encoding="utf-8")
        legacy_manifest = legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME
        legacy_manifest.write_text(
            json.dumps(
                {
                    "managed": [
                        "run-verify.py",
                        "run-codex-plan-review.py",
                        "run-codex-impl-review.py",
                        "run-codex-impl-cycle.py",
                        "fix_codex_plugin_prompts.py",
                    ],
                    "preset": "python",
                    "template": "codex-main",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Plant unmanaged user files at the new claude/agents destinations for
        # run-verify.py and run-codex-plan-review.py — copy must skip them in
        # update mode (force=True, overwrite_unmanaged=False).
        new_run_verify = self.repo_root / ".claude" / "scripts" / "run-verify.py"
        new_run_verify.parent.mkdir(parents=True, exist_ok=True)
        new_run_verify.write_text("user-owned-verify\n", encoding="utf-8")
        new_codex_plan = self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py"
        new_codex_plan.parent.mkdir(parents=True, exist_ok=True)
        new_codex_plan.write_text("user-owned-plan\n", encoding="utf-8")
        # Seed manifests so smart-mode picks codex-main update.
        agents_dir = self.repo_root / ".agents"
        (agents_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["AGENTS.md", "skills/codex-plan/SKILL.md"], "preset": "python", "template": "codex-main"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main([])
        self.assertEqual(exit_code, 0)

        # Skipped-copy legacy files preserved (along with the user's content at the new path).
        self.assertTrue((legacy_scripts / "run-verify.py").is_file())
        self.assertEqual(new_run_verify.read_text(encoding="utf-8"), "user-owned-verify\n")
        self.assertTrue((legacy_scripts / "run-codex-plan-review.py").is_file())
        self.assertEqual(new_codex_plan.read_text(encoding="utf-8"), "user-owned-plan\n")
        # Successfully migrated legacy files removed.
        self.assertFalse((legacy_scripts / "run-codex-impl-review.py").exists())
        self.assertFalse((legacy_scripts / "run-codex-impl-cycle.py").exists())
        self.assertFalse((legacy_scripts / "fix_codex_plugin_prompts.py").exists())
        # Legacy manifest re-written to track only the surviving entries.
        self.assertTrue(legacy_manifest.is_file())
        surviving = json.loads(legacy_manifest.read_text(encoding="utf-8"))
        self.assertEqual(set(surviving["managed"]), {"run-verify.py", "run-codex-plan-review.py"})

    def test_codex_main_init_aborts_atomically_on_claude_only_collision(self) -> None:
        # Regression for the multi-destination preflight: a collision that
        # exists only under .claude/scripts must abort BEFORE any .agents/scripts
        # files are written. Pre-(C) `copy_runner_files` checked all runner
        # collisions in one pass, so init never left a half-installed scaffold.
        new_run_verify = self.repo_root / ".claude" / "scripts" / "run-verify.py"
        new_run_verify.parent.mkdir(parents=True, exist_ok=True)
        new_run_verify.write_text("user-owned-verify\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(exit_code, 1)
        # No agents-side files written — the preflight aborted before the first copy.
        self.assertFalse((self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py").exists())
        self.assertFalse((self.repo_root / ".agents" / "scripts").exists())
        # User collision file untouched.
        self.assertEqual(new_run_verify.read_text(encoding="utf-8"), "user-owned-verify\n")

    def test_codex_main_init_aborts_when_destination_path_is_a_file(self) -> None:
        # Regression: if .claude/scripts (or .agents/scripts) exists as a FILE
        # rather than a directory, a later mkdir(...exist_ok=True) would raise
        # FileExistsError mid-flow. Preflight must catch it before any copy.
        agents_scripts_path = self.repo_root / ".agents" / "scripts"
        agents_scripts_path.parent.mkdir(parents=True, exist_ok=True)
        agents_scripts_path.write_text("blocking file\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(exit_code, 1)
        # The blocking file is untouched, no scaffold created.
        self.assertTrue(agents_scripts_path.is_file())
        self.assertEqual(agents_scripts_path.read_text(encoding="utf-8"), "blocking file\n")

    def test_legacy_scripts_carry_forward_recovers_partial_migration(self) -> None:
        # Regression: a previous failed migration may have left both a legacy
        # scripts/verify-config.json (with user customizations) AND a generic
        # .claude/scripts/verify-config.json (preset defaults). Carry-forward
        # must prefer the legacy content over the generic new file.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        custom_config = {
            "VERIFY_CMD": "echo legacy-customized",
            "VERIFY_SHELL": "direct",
            "PRIMARY_LOG_DIR": "custom/legacy",
        }
        (legacy_scripts / "verify-config.json").write_text(
            json.dumps(custom_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for name in ("run-verify.py", "run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py", "fix_codex_plugin_prompts.py"):
            (legacy_scripts / name).write_text("legacy\n", encoding="utf-8")
        (legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "managed": [
                        "verify-config.json",
                        "run-verify.py",
                        "run-codex-plan-review.py",
                        "run-codex-impl-review.py",
                        "run-codex-impl-cycle.py",
                        "fix_codex_plugin_prompts.py",
                    ],
                    "preset": "python",
                    "template": "codex-main",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Plant a generic new-location file (simulates partial migration result).
        new_verify = self.repo_root / ".claude" / "scripts" / "verify-config.json"
        new_verify.parent.mkdir(parents=True, exist_ok=True)
        new_verify.write_text(
            json.dumps(
                {"VERIFY_CMD": "python -m pytest", "VERIFY_SHELL": "direct", "PRIMARY_LOG_DIR": ".agents/logs/verify"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Mark the new file as init-managed so carry-forward recognizes it as a
        # prior partial-migration artifact rather than a user-owned file.
        (new_verify.parent / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["verify-config.json"], "preset": "python", "template": "codex-main"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Seed manifests so smart-mode picks codex-main update.
        agents_dir = self.repo_root / ".agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["AGENTS.md", "skills/codex-plan/SKILL.md"], "preset": "python", "template": "codex-main"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main([])
        self.assertEqual(exit_code, 0)

        # Carry-forward overwrote the generic new file with the legacy content.
        self.assertEqual(json.loads(new_verify.read_text(encoding="utf-8")), custom_config)
        # Legacy verify-config removed (cleanup ran because migration succeeded).
        self.assertFalse((legacy_scripts / "verify-config.json").exists())

    def test_legacy_scripts_carry_forward_preserves_user_owned_new_file(self) -> None:
        # Regression: if the user manually created .claude/scripts/verify-config.json
        # (not tracked in any new-location manifest), carry-forward must not
        # overwrite it with legacy content. The legacy file is treated as a
        # collision-skip — preserved in scripts/ so nothing is silently lost.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        legacy_config = {"VERIFY_CMD": "echo legacy", "VERIFY_SHELL": "direct", "PRIMARY_LOG_DIR": "legacy/log"}
        (legacy_scripts / "verify-config.json").write_text(
            json.dumps(legacy_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for name in ("run-verify.py", "run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py", "fix_codex_plugin_prompts.py"):
            (legacy_scripts / name).write_text("legacy\n", encoding="utf-8")
        (legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "managed": ["verify-config.json", "run-verify.py", "run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py", "fix_codex_plugin_prompts.py"],
                    "preset": "python",
                    "template": "codex-main",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # User-owned file at the new location, NO new-location manifest.
        user_config = {"VERIFY_CMD": "echo user-owned", "VERIFY_SHELL": "direct", "PRIMARY_LOG_DIR": "user/log"}
        new_verify = self.repo_root / ".claude" / "scripts" / "verify-config.json"
        new_verify.parent.mkdir(parents=True, exist_ok=True)
        new_verify.write_text(json.dumps(user_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Smart-mode → codex-main update.
        agents_dir = self.repo_root / ".agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["AGENTS.md", "skills/codex-plan/SKILL.md"], "preset": "python", "template": "codex-main"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main([])
        self.assertEqual(exit_code, 0)

        # User-owned new file untouched.
        self.assertEqual(json.loads(new_verify.read_text(encoding="utf-8")), user_config)
        # Legacy verify-config preserved (cleanup keeps unmigrated entries).
        self.assertTrue((legacy_scripts / "verify-config.json").is_file())
        self.assertEqual(json.loads((legacy_scripts / "verify-config.json").read_text(encoding="utf-8")), legacy_config)

    def test_codex_main_update_mode_aborts_when_destination_path_is_a_file(self) -> None:
        # Regression: structural preflight (non-directory at destination path)
        # must fire in update/fresh modes too, not just init mode. Otherwise
        # mkdir(...exist_ok=True) raises mid-flow after .agents/scripts copies
        # already wrote files.
        agents_scripts_path = self.repo_root / ".agents" / "scripts"
        agents_scripts_path.parent.mkdir(parents=True, exist_ok=True)
        agents_scripts_path.write_text("blocking file\n", encoding="utf-8")
        # Seed manifests so smart-mode picks codex-main update.
        (self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["AGENTS.md", "skills/codex-plan/SKILL.md"], "preset": "python", "template": "codex-main"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["--update"])
        self.assertEqual(exit_code, 1)
        # Blocking file untouched.
        self.assertEqual(agents_scripts_path.read_text(encoding="utf-8"), "blocking file\n")

    def test_project_init_aborts_when_destination_path_is_a_file(self) -> None:
        # Regression: standard templates must run the structural preflight too,
        # otherwise .claude/CLAUDE.md, .claude/settings.json, .claude/hooks etc.
        # get written before .claude/scripts mkdir fails on a non-dir blocker.
        claude_scripts_path = self.repo_root / ".claude" / "scripts"
        claude_scripts_path.parent.mkdir(parents=True, exist_ok=True)
        claude_scripts_path.write_text("blocking file\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "project-init", "python"])
        self.assertEqual(exit_code, 1)
        # No .claude/* writes occurred — preflight aborted before any I/O.
        self.assertTrue(claude_scripts_path.is_file())
        self.assertEqual(claude_scripts_path.read_text(encoding="utf-8"), "blocking file\n")
        self.assertFalse((self.repo_root / ".claude" / "CLAUDE.md").exists())
        self.assertFalse((self.repo_root / ".claude" / "settings.json").exists())

    def test_split_scripts_corrupt_manifest_surfaces_before_any_writes(self) -> None:
        # Regression: a malformed .agents/scripts/.claude-dotfiles-managed.json
        # or .claude/scripts/.claude-dotfiles-managed.json would otherwise be
        # read strictly later inside copy_runner_files_to / prune calls, after
        # copy_template_tree() has already mutated the repo. Preflight must
        # validate split-layout manifests too.
        agents_scripts_manifest = self.repo_root / ".agents" / "scripts" / self.runner.WORKFLOW_MANIFEST_NAME
        agents_scripts_manifest.parent.mkdir(parents=True, exist_ok=True)
        agents_scripts_manifest.write_text("{not json{\n", encoding="utf-8")
        # Smart-mode → codex-main update.
        (self.repo_root / ".agents" / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            json.dumps(
                {"managed": ["AGENTS.md", "skills/codex-plan/SKILL.md"], "preset": "python", "template": "codex-main"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["--update"])
        self.assertEqual(exit_code, 1)
        # No new writes — preflight aborted.
        self.assertFalse((self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py").exists())
        self.assertFalse((self.repo_root / ".claude" / "scripts").exists())

    def test_legacy_scripts_cleanup_keeps_manifest_when_unlink_fails(self) -> None:
        # Regression: if a legacy file can't be unlinked (locked / read-only,
        # common on Windows), cleanup must keep that entry in the manifest so
        # the next run retries instead of orphaning the file.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        unlinkable = legacy_scripts / "run-codex-impl-cycle.py"
        unlinkable.write_text("legacy stuck\n", encoding="utf-8")
        manifest_path = legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME
        manifest_path.write_text(
            json.dumps({"managed": ["run-codex-impl-cycle.py"]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        # Simulate a locked file by patching Path.unlink to raise PermissionError
        # for this specific path only.
        original_unlink = self.runner.Path.unlink
        def fake_unlink(self_path, *args, **kwargs):
            if self_path == unlinkable:
                raise PermissionError("simulated lock")
            return original_unlink(self_path, *args, **kwargs)

        with mock.patch.object(self.runner.Path, "unlink", fake_unlink):
            self.runner.migrate_legacy_scripts_cleanup(
                self.repo_root,
                new_scripts_present={"run-codex-impl-cycle.py"},
                template_runner_names={"run-codex-impl-cycle.py"},
            )

        # File still on disk, manifest preserved with the locked entry.
        self.assertTrue(unlinkable.is_file())
        self.assertTrue(manifest_path.is_file())
        surviving = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIn("run-codex-impl-cycle.py", surviving["managed"])

    def test_legacy_scripts_corrupt_manifest_surfaces_error_in_non_fresh_modes(self) -> None:
        # Regression: a corrupt legacy scripts/.claude-dotfiles-managed.json
        # must NOT be silently swallowed in normal init/update modes — the
        # tolerant fallback is reserved for --fresh recovery. Otherwise the
        # repo's manifest corruption stays hidden and migration silently does
        # nothing.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        (legacy_scripts / "verify-config.json").write_text("{\"VERIFY_CMD\":\"old\"}\n", encoding="utf-8")
        (legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME).write_text("{not json{\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(exit_code, 1)
        # Legacy file untouched — migration helpers never ran past the parse.
        self.assertTrue((legacy_scripts / "verify-config.json").is_file())
        # CRITICAL: no new files written either — early validation aborted
        # before any I/O so the user can fix the manifest without a half-
        # migrated tree.
        self.assertFalse((self.repo_root / ".agents" / "scripts").exists())
        self.assertFalse((self.repo_root / ".claude" / "scripts").exists())
        self.assertFalse((self.repo_root / ".agents" / "AGENTS.md").exists())

    def test_legacy_scripts_migration_recovers_from_malformed_manifest_under_fresh(self) -> None:
        # Regression: --fresh is a recovery path and must tolerate corrupted
        # legacy/new manifests in the migration helpers; otherwise a half-
        # migrated repo with broken manifests cannot be repaired.
        legacy_scripts = self.repo_root / "scripts"
        legacy_scripts.mkdir(parents=True, exist_ok=True)
        for name in ("run-verify.py", "verify-config.json", "run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py", "fix_codex_plugin_prompts.py"):
            (legacy_scripts / name).write_text("legacy\n", encoding="utf-8")
        # Older retired shell runners that may have been managed by previous versions.
        retired_legacy = ("run-verify.sh", "run-verify.ps1", "run-codex-plan-review.ps1", "run-codex-impl-review.ps1")
        for name in retired_legacy:
            (legacy_scripts / name).write_text("legacy retired\n", encoding="utf-8")
        # Malformed legacy manifest.
        (legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME).write_text(
            "{not json{\n",
            encoding="utf-8",
        )
        # Malformed new-location manifest at .claude/scripts.
        new_scripts_manifest = self.repo_root / ".claude" / "scripts" / self.runner.WORKFLOW_MANIFEST_NAME
        new_scripts_manifest.parent.mkdir(parents=True, exist_ok=True)
        new_scripts_manifest.write_text("{also-not-json\n", encoding="utf-8")
        # Pre-existing partial-migration verify-config at the new path.
        (self.repo_root / ".claude" / "scripts" / "verify-config.json").write_text(
            "{\"VERIFY_CMD\":\"old\"}\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python", "--fresh"])
        self.assertEqual(exit_code, 0)
        # New layout in place; the broken legacy manifest didn't block recovery.
        self.assertTrue((self.repo_root / ".agents" / "scripts" / "run-codex-plan-review.py").is_file())
        self.assertTrue((self.repo_root / ".claude" / "scripts" / "run-verify.py").is_file())
        # Canonical-runner-set fallback lets cleanup remove the legacy files
        # even though the manifest itself was unparseable. No orphans left,
        # including older retired shell runners.
        for name in ("run-verify.py", "verify-config.json", "run-codex-plan-review.py", "run-codex-impl-review.py", "run-codex-impl-cycle.py", "fix_codex_plugin_prompts.py", *retired_legacy):
            self.assertFalse((legacy_scripts / name).exists(), name)
        self.assertFalse((legacy_scripts / self.runner.WORKFLOW_MANIFEST_NAME).exists())

    def test_init_mode_errors_on_collision_without_manifest(self) -> None:
        # Init mode (no --fresh, no manifest) must refuse to half-install when a template
        # path already exists as an unmanaged user file.
        agents_md = self.repo_root / ".agents" / "AGENTS.md"
        agents_md.parent.mkdir(parents=True, exist_ok=True)
        agents_md.write_text("user owned\n", encoding="utf-8")

        with mock.patch.object(self.runner, "discover_portable_python_launcher", return_value="python3"):
            with chdir(self.repo_root):
                exit_code = self.runner.main(["-t", "codex-main", "python"])
        self.assertEqual(exit_code, 1)
        # User file preserved (no half-install).
        self.assertEqual(agents_md.read_text(encoding="utf-8"), "user owned\n")
