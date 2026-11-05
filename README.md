# AI Cheap Setup

Set up [AI Cheap](https://aicheap.io/) for **Codex CLI** and **local Codex in the
ChatGPT desktop app**, with **GPT-6.1-Sol** as the default model.

| Client | macOS | Windows, without WSL |
| --- | --- | --- |
| Codex CLI | Supported | Supported |
| ChatGPT desktop app: Codex → This computer | Supported | Supported |

This configures the desktop app's local Codex agents. It does not redirect
regular Chat or managed ChatGPT Work conversations. OpenAI documents the
[shared agent settings and separate ChatGPT Work settings](https://learn.chatgpt.com/docs/developer-settings).
Linux CLI use is also supported.

## Requirements

- [Python 3.11 or newer](https://www.python.org/downloads/), available as
  `python3` on macOS or `py` / `python` on Windows. No Python packages are needed.
- For CLI setup: an existing current Codex CLI, or [Node.js with npm](https://nodejs.org/)
  so the installer can install `@openai/codex`.
- For desktop use: install the current ChatGPT desktop app separately.
- An API key and model access from [the AI Cheap console](https://console.aicheap.io/).

## macOS

Download and inspect the installer, then run it:

```sh
curl -fsSLo setup-codex.py https://raw.githubusercontent.com/trungdlp/aicheap-setup/HEAD/setup-codex.py
python3 setup-codex.py
```

If you cloned the repository, `bash setup-codex.sh` also locates an installed
Python 3.11+ automatically. For desktop use without installing the CLI:

```sh
python3 setup-codex.py --desktop-only
```

## Windows (native PowerShell)

Download and inspect the installer, then run it in PowerShell:

```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/trungdlp/aicheap-setup/HEAD/setup-codex.py -OutFile setup-codex.py
py -3 setup-codex.py
```

Use `python` instead of `py -3` if Python was installed without the `py` launcher.
No WSL, Git Bash, administrator session, or persistent execution-policy change
is required. From a clone, you can also use the PowerShell entry point:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup-codex.ps1
```

For desktop use without installing the CLI, run `py -3 setup-codex.py --desktop-only`
or pass `-DesktopOnly` to the PowerShell entry point.

## Start using it

The installer prompts for your API key without displaying it. It makes AI Cheap
the default provider in your user-level Codex configuration:

| OS | Configuration file |
| --- | --- |
| macOS | `~/.codex/config.toml` |
| Windows | `%USERPROFILE%\.codex\config.toml` |

For the CLI, start a new session:

```sh
codex
codex exec "Explain this repository"
codex -m ANOTHER_AVAILABLE_MODEL
```

If PowerShell blocks npm's `codex.ps1`, use `codex.cmd` instead.
The existing macOS/Linux `codex-aicheap` command remains a compatibility alias
when `~/.local/bin` is on `PATH`.

For the desktop app, **fully quit and reopen ChatGPT**, select **Codex** from the
ChatGPT dropdown, choose **This computer**, and start a new chat. The app reads
the same configuration. Authentication reads the saved key directly, so you
can open the app normally from the Dock or Start menu.

Check `/status` in the CLI, or inspect the model and provider in the app, before
using it. Existing profiles or administrator policies can override user defaults.
See OpenAI's [gateway configuration and verification instructions](https://learn.chatgpt.com/docs/enterprise/connect-to-a-gateway).

## What setup changes

- Replaces the top-level `model` / `model_provider` defaults and the `aicheap`
  provider in `config.toml`, preserving unrelated settings and login files.
- Saves the original configuration as `config.toml.backup-TIMESTAMP` before
  changing it. Invalid or conflicting TOML is rejected before configuration writes.
- Stores the key beside `config.toml` in `aicheap-api-key`, with owner-only
  permissions on macOS/Linux and an ACL restricted to the current user on Windows.
- Registers the installed Python executable as a credential helper. Keep that
  Python installation available; rerun setup if you move or remove it.

The key and configuration backups are plaintext local files. API keys are never
put in `config.toml` or shell startup files. Your prompts and code go through
[AI Cheap's documented Codex endpoint](https://aicheap.io/docs#codex),
`https://api.aicheap.io/openai/v1`, using the Responses API.

## Repeat setup and automation

Rerunning setup reuses the saved key and does not create another backup when
the configuration is unchanged. Inject `AICHEAP_API_KEY` through your secret
manager's environment to replace the saved key or skip the prompt. The credential
helper also accepts that variable at runtime when it is available to the client.
Avoid putting credentials in command arguments or shell history.

`CODEX_HOME` overrides the configuration directory. For desktop use, leave it
unset unless the app is configured to use that same directory.

Setup makes no AI API requests and does not verify your key, subscription, or
model availability. A successful connection should also be confirmed in your
AI Cheap usage dashboard.

## Undo setup

Fully quit the clients. Restore the `config.toml.backup-TIMESTAMP` printed during
setup to `config.toml`. If no config existed before setup, remove the generated
`config.toml` instead. Then remove `aicheap-api-key` from that directory and, on
macOS/Linux, `~/.local/bin/codex-aicheap` if present. Codex and Python are left
installed.

## Checks

Tests run on macOS, native Windows, and Linux with isolated configuration files,
fake credentials, and a fake npm installer. No paid API requests are made.

```sh
python3 -m unittest discover -s tests -v
```

On Windows, use `py -3 -m unittest discover -s tests -v`.
