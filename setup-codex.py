#!/usr/bin/env python3
"""Configure AI Cheap for Codex CLI and local Codex in the ChatGPT desktop app."""
import argparse
import csv
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if sys.version_info < (3, 11):
    sys.exit("Python 3.11 or newer is required; on macOS, try bash setup-codex.sh.")

import tomllib
import warnings


MODEL = "gpt-6.1-sol"
BASE_URL = "https://api.aicheap.io/openai/v1"
TOKEN_COMMAND = (
    'import os,pathlib,sys;'
    'sys.stdout.write(os.environ.get("AICHEAP_API_KEY") '
    'or pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))'
)


def merge_config(original, key_file):
    """Keep original TOML statements, replacing only our provider and defaults."""
    tomllib.loads(original)
    kept = []
    pending = ""
    at_root = True
    skip = False
    for line in original.splitlines(keepends=True):
        pending += line
        try:
            statement = tomllib.loads(pending)
        except tomllib.TOMLDecodeError:
            continue
        if pending.lstrip().startswith("["):
            at_root = False
            skip = "aicheap" in statement.get("model_providers", {})
        if not skip and not (at_root and {"model", "model_provider"} & statement.keys()):
            kept.append(pending)
        pending = ""
    if pending:
        raise ValueError("Could not safely merge config.toml.")

    quote = lambda value: json.dumps(value, ensure_ascii=False)
    merged = (
        f'model = {quote(MODEL)}\nmodel_provider = "aicheap"\n'
        + "".join(kept).rstrip() + "\n\n"
        '[model_providers.aicheap]\n'
        'name = "AI Cheap"\n'
        f'base_url = {quote(BASE_URL)}\n'
        'wire_api = "responses"\n'
        'requires_openai_auth = false\n\n'
        '[model_providers.aicheap.auth]\n'
        f'command = {quote(sys.executable)}\n'
        f'args = {quote(["-c", TOKEN_COMMAND, str(key_file)])}\n'
    )
    # Refuse unusual conflicting TOML rather than risking an invalid config.
    tomllib.loads(merged)
    return merged


def secure_write(path, data, mode=0o600):
    """Set permissions before writing credentials, then replace atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            if os.name == "nt":
                identity = subprocess.check_output(
                    ["whoami", "/user", "/fo", "csv", "/nh"], text=True
                )
                sid = next(csv.reader(identity.splitlines()))[1]
                # Drop explicit default grants too, before storing any credentials.
                subprocess.run(["icacls", temporary, "/reset"],
                               check=True, capture_output=True)
                subprocess.run(
                    ["icacls", temporary, "/inheritance:r", "/grant:r", f"*{sid}:F"],
                    check=True, capture_output=True,
                )
            else:
                os.fchmod(stream.fileno(), mode)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def install_cli():
    if shutil.which("codex"):
        return
    npm = shutil.which("npm")
    if not npm:
        raise ValueError("Install Node.js with npm first, or use --desktop-only.")
    # npm does not need the gateway credential during package installation.
    env = {k: v for k, v in os.environ.items() if k != "AICHEAP_API_KEY"}
    subprocess.run([npm, "install", "-g", "@openai/codex"], check=True, env=env)
    if not shutil.which("codex"):
        raise ValueError("Add the npm global bin directory to PATH, then rerun setup.")


def setup(desktop_only=False):
    codex_dir = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").resolve()
    key_file = codex_dir / "aicheap-api-key"
    config_file = codex_dir / "config.toml"
    original = config_file.read_bytes() if config_file.exists() else b""
    merged = merge_config(original.decode("utf-8-sig"), key_file).encode("utf-8")

    if not desktop_only:
        install_cli()
    credential = os.environ.get("AICHEAP_API_KEY")
    if not credential and key_file.is_file():
        credential = key_file.read_text(encoding="utf-8")
    if not credential:
        print("Create an API key at https://console.aicheap.io/")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            credential = getpass.getpass("AI Cheap API key: ")
    if not credential or any(c.isspace() for c in credential):
        raise ValueError("API key must be nonempty and contain no whitespace.")

    if original and original != merged:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = codex_dir / f"config.toml.backup-{timestamp}"
        secure_write(backup, original)
        print(f"Configuration backup: {backup}")
    secure_write(key_file, credential.encode("utf-8"))
    if original != merged:
        secure_write(config_file, merged)

    if not desktop_only and os.name != "nt":
        launcher = Path.home() / ".local/bin/codex-aicheap"
        secure_write(launcher, b'#!/usr/bin/env bash\nexec codex "$@"\n', 0o700)
        print(f"Compatibility launcher: {launcher}")
    print(f"Configured {config_file}")
    print(f"Default provider: AI Cheap; model: {MODEL}")
    print("Fully quit and reopen the ChatGPT desktop app, then select Codex / This computer.")
    print("For the CLI, run codex and use /status to verify the provider and model.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop-only", action="store_true",
                        help="configure the desktop app without installing the CLI")
    args = parser.parse_args()
    try:
        setup(args.desktop_only)
    except tomllib.TOMLDecodeError:
        parser.exit(1, "Could not safely merge config.toml; configuration was not changed.\n")
    except (OSError, ValueError, EOFError, getpass.GetPassWarning, subprocess.CalledProcessError):
        # Credential-related exceptions can include input; never print their payload.
        parser.exit(1, "Setup failed. Check config.toml, Python/Node installation, key, and file permissions.\n")


if __name__ == "__main__":
    main()
