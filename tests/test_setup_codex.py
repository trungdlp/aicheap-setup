"""Offline setup tests, including native file permissions and credential lookup."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("setup_codex", ROOT / "setup-codex.py")
SETUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETUP)


class CodexSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex setup ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config_dir = self.home / "custom codex"
        self.config_dir.mkdir()
        self.config = self.config_dir / "config.toml"
        self.key = self.config_dir / "aicheap-api-key"
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        CODEX_HOME=str(self.config_dir))
        self.env["AICHEAP_API_KEY"] = "example"
        patch = mock.patch.dict(os.environ, self.env, clear=True)
        patch.start()
        self.addCleanup(patch.stop)

    def setup(self, desktop_only=True):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            SETUP.setup(desktop_only)
        self.assertNotIn("example", output.getvalue())
        return tomllib.loads(self.config.read_text(encoding="utf-8"))

    def test_merge_preserves_other_settings_and_handles_multiline_toml(self):
        original = '''# Keep this comment
"model" = "old"
model_provider = "other"
approval_policy = "on-request"
developer_instructions = """Keep literal text:
[model_providers.aicheap]
model = "inside a string"
"""
[mcp_servers.example]
command = "keep-me"
args = [
  "one", "two",
]
[model_providers.other]
name = "Other"
base_url = "https://example.com/v1"
[model_providers."aicheap"]
name = "Old AI Cheap"
env_key = "OLD_KEY"
[model_providers.aicheap.auth]
command = "old-helper"
[projects."C:\\\\a project"]
trust_level = "trusted"
'''
        self.config.write_bytes(original.encode())
        auth = self.config_dir / "auth.json"
        auth.write_bytes(b"existing login\n")
        result = self.setup()
        before = tomllib.loads(original)
        for key in ("approval_policy", "developer_instructions", "mcp_servers", "projects"):
            self.assertEqual(result[key], before[key])
        self.assertEqual(result["model_providers"]["other"], before["model_providers"]["other"])
        self.assertEqual(result["model"], "GPT-6.1-Sol")
        self.assertEqual(result["model_provider"], "aicheap")
        self.assertNotIn("env_key", result["model_providers"]["aicheap"])
        self.assertIn("# Keep this comment", self.config.read_text())
        self.assertEqual(auth.read_bytes(), b"existing login\n")
        backups = list(self.config_dir.glob("config.toml.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original.encode())

    def test_rerun_is_idempotent_and_desktop_helper_needs_no_environment_key(self):
        result = self.setup()
        first = self.config.read_bytes()
        del os.environ["AICHEAP_API_KEY"]
        self.setup()
        self.assertEqual(self.config.read_bytes(), first)
        self.assertFalse(list(self.config_dir.glob("config.toml.backup-*")))
        provider = result["model_providers"]["aicheap"]
        self.assertEqual(provider["base_url"], SETUP.BASE_URL)
        self.assertEqual(provider["wire_api"], "responses")
        self.assertFalse(provider["requires_openai_auth"])
        helper = provider["auth"]
        credential = subprocess.check_output([helper["command"], *helper["args"]], text=True)
        self.assertEqual(credential, "example")
        self.assertNotIn("example", self.config.read_text())

    def test_invalid_config_and_key_leave_existing_files_unchanged(self):
        self.setup()
        original = self.config.read_bytes()
        for key in ("bad key", "bad\nkey", "bad\rkey"):
            with mock.patch.dict(os.environ, AICHEAP_API_KEY=key):
                with self.assertRaises(ValueError):
                    self.setup()
            self.assertEqual(self.config.read_bytes(), original)
            self.assertEqual(self.key.read_text(), "example")
        invalid = b'model = "unterminated\n'
        self.config.write_bytes(invalid)
        with self.assertRaises(tomllib.TOMLDecodeError):
            self.setup()
        self.assertEqual(self.config.read_bytes(), invalid)
        self.assertFalse(list(self.config_dir.glob("config.toml.backup-*")))

    def test_native_key_permissions(self):
        self.setup()
        if os.name == "nt":
            env = dict(os.environ, AICHEAP_TEST_FILE=str(self.key))
            command = (
                '$acl = [IO.File]::GetAccessControl($env:AICHEAP_TEST_FILE); '
                '$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value; '
                '$rules = @($acl.GetAccessRules($true, $true, '
                '[Security.Principal.SecurityIdentifier])); '
                '@{ Protected = $acl.AreAccessRulesProtected; CurrentUser = $sid; '
                'Rules = @($rules | ForEach-Object { '
                '@{ User = $_.IdentityReference.Value; Inherited = $_.IsInherited; '
                'Rights = $_.FileSystemRights.ToString() } }) } | ConvertTo-Json -Depth 4; '
                'if (-not $acl.AreAccessRulesProtected -or $rules.Count -ne 1 '
                '-or $rules[0].IdentityReference.Value -ne $sid) { exit 1 }'
            )
            result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)

    def test_native_entrypoint_configures_desktop_without_cli(self):
        if os.name == "nt":
            command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                       "-File", str(ROOT / "setup-codex.ps1"), "-DesktopOnly"]
        else:
            command = ["bash", str(ROOT / "setup-codex.sh"), "--desktop-only"]
        result = subprocess.run(command, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("example", result.stdout + result.stderr)
        self.assertEqual(tomllib.loads(self.config.read_text())["model_provider"], "aicheap")

    def test_cli_install_and_failure_do_not_pass_credentials_to_npm(self):
        npm = self.home / ("npm.cmd" if os.name == "nt" else "npm")
        codex = self.home / ("codex.cmd" if os.name == "nt" else "codex")
        if os.name == "nt":
            npm.write_text('@echo off\r\nif defined AICHEAP_API_KEY exit /b 1\r\n'
                           'type nul > "%~dp0codex.cmd"\r\n')
        else:
            npm.write_text('#!/bin/sh\n[ -z "${AICHEAP_API_KEY:-}" ] || exit 1\n'
                           'touch "$(dirname "$0")/codex"\n')
            npm.chmod(0o700)

        def which(name):
            if name == "npm":
                return str(npm)
            return str(codex) if codex.exists() else None

        with mock.patch.object(SETUP.shutil, "which", side_effect=which):
            self.setup(desktop_only=False)
        self.assertTrue(codex.exists())
        if os.name != "nt":
            launcher = self.home / ".local/bin/codex-aicheap"
            self.assertTrue(launcher.stat().st_mode & 0o100)
        with mock.patch.object(SETUP.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "Install Node.js"):
                SETUP.install_cli()

    def test_windows_paths_are_escaped_in_toml(self):
        path = "C:\\Users\\a user\\.codex\\aicheap-api-key"
        result = tomllib.loads(SETUP.merge_config("", path))
        self.assertEqual(result["model_providers"]["aicheap"]["auth"]["args"][-1], path)


if __name__ == "__main__":
    unittest.main()
