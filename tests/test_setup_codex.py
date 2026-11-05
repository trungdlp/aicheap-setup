#!/usr/bin/env python3
"""Exercise setup and launcher in an isolated home without network or real keys."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "setup-codex.sh"


class CodexSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex setup ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        codex = self.bin / "codex"
        codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "assert os.environ['AICHEAP_API_KEY'] == 'example'\n"
            "print(json.dumps(sys.argv[1:]))\n"
        )
        codex.chmod(0o700)
        self.env = dict(os.environ, HOME=str(self.home),
                        CODEX_HOME=str(self.home / "custom codex"),
                        PATH=f"{self.bin}:{os.environ['PATH']}")
        self.env["AICHEAP_API_KEY"] = "example"
        self.launcher = self.home / ".local/bin/codex-aicheap"
        self.key = Path(self.env["CODEX_HOME"]) / "aicheap-api-key"

    def setup(self, env=None, *args):
        return subprocess.run(["bash", str(SCRIPT), *args],
                              env=self.env if env is None else env,
                              capture_output=True, text=True)

    def test_install_rerun_and_launch_preserve_config_and_auth(self):
        config_dir = self.key.parent
        config_dir.mkdir()
        for name in ("config.toml", "auth.json"):
            (config_dir / name).write_text("existing content\n")
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("example", result.stdout + result.stderr)
        self.assertEqual(self.key.read_text(), "example")
        self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.launcher.stat().st_mode & 0o777, 0o700)
        env = self.env.copy()
        del env["AICHEAP_API_KEY"]
        self.assertEqual(self.setup(env).returncode, 0)
        result = subprocess.run([str(self.launcher), "exec", "-m", "other-model",
                                 "a prompt with spaces; $(false)"],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(result.stdout)
        self.assertIn('model_provider="aicheap"', args)
        self.assertIn('model="GPT-6.1-Sol"', args)
        self.assertIn('base_url="https://api.aicheap.io/openai/v1"', args[5])
        self.assertIn('env_key="AICHEAP_API_KEY"', args[5])
        self.assertIn('wire_api="responses"', args[5])
        self.assertEqual(args[6:], ["exec", "-m", "other-model",
                                    "a prompt with spaces; $(false)"])
        for name in ("config.toml", "auth.json"):
            self.assertEqual((config_dir / name).read_text(), "existing content\n")
        self.key.unlink()
        result = subprocess.run([str(self.launcher)], env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("key missing", result.stderr)

    def test_invalid_key_and_arguments_do_not_overwrite_credentials(self):
        self.assertEqual(self.setup().returncode, 0)
        for key in ("bad key", "bad\nkey"):
            env = dict(self.env, AICHEAP_API_KEY=key)
            result = self.setup(env)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(key, result.stdout + result.stderr)
            self.assertEqual(self.key.read_text(), "example")
        self.assertNotEqual(self.setup(self.env, "unexpected").returncode, 0)
        self.assertFalse(list(self.key.parent.glob(".aicheap-key.*")))

    def test_missing_codex_installs_with_npm_and_reports_missing_npm(self):
        (self.bin / "codex").unlink()
        for command in ("bash", "mkdir", "mktemp", "cat", "chmod", "mv", "rm"):
            (self.bin / command).symlink_to(shutil.which(command))
        env = dict(self.env, PATH=str(self.bin))
        result = self.setup(env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Install Node.js", result.stderr)
        self.assertFalse(self.key.exists())
        npm = self.bin / "npm"
        npm.write_text(
            '#!/usr/bin/env bash\nset -eu\n'
            '[[ "$*" == "install -g @openai/codex" ]]\n'
            'printf "#!/usr/bin/env bash\\nexit 0\\n" > "$HOME/bin/codex"\n'
            'chmod 700 "$HOME/bin/codex"\n'
        )
        npm.chmod(0o700)
        result = self.setup(env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.launcher.exists())


if __name__ == "__main__":
    unittest.main()
