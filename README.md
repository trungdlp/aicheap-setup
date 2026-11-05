# AI Cheap Setup

Setup scripts for using coding tools with [AI Cheap](https://aicheap.io/).
Currently supports **Codex CLI** on macOS and Linux (including WSL).

## Set up Codex

Download and inspect the installer, then run it:

```sh
curl -fsSLo setup-codex.sh https://raw.githubusercontent.com/trungdlp/aicheap-setup/HEAD/setup-codex.sh
bash setup-codex.sh
~/.local/bin/codex-aicheap
```

Or clone this repository and run `bash setup-codex.sh` from its root.

The script uses your existing Codex CLI, or installs `@openai/codex` with npm
if needed. Install Node.js with npm first if neither is available. It prompts
for an API key from [the AI Cheap console](https://console.aicheap.io/) without
displaying it. An active AI Cheap plan and a key with model access are required.

Add `~/.local/bin` to your shell's `PATH` to use the short command:

```sh
codex-aicheap
codex-aicheap -m GPT-6.1-Sol
codex-aicheap exec "Explain this repository"
```

## What setup changes

- Installs the `codex-aicheap` launcher in `~/.local/bin`.
- Saves the API key in `${CODEX_HOME:-$HOME/.codex}/aicheap-api-key` with
  owner-only permissions (`600`). The key is plaintext on disk.
- Uses `GPT-6.1-Sol` by default; choose another available model with `-m MODEL`.

The launcher uses AI Cheap's [documented Codex endpoint](https://aicheap.io/docs#codex),
`https://api.aicheap.io/openai/v1`, with the Responses API through a
[custom Codex provider](https://learn.chatgpt.com/docs/config-file/config-advanced).
Your prompts and code sent by this launcher go through AI Cheap.

Existing Codex settings, login, shell startup files, and the normal `codex`
command are unchanged. This configures the CLI launcher; it does not configure
the desktop app or IDE extension.

## Repeat setup and automation

Rerunning setup reuses the saved key. Supply `AICHEAP_API_KEY` in the environment
to replace it, or to run setup without a prompt. Inject credentials through your
secret manager rather than putting keys in command arguments or shell history.
The launcher also accepts an `AICHEAP_API_KEY` environment variable instead of
reading the saved file.

Use the same `CODEX_HOME` during setup and launch if you customize it. No API
requests are made during installation, so setup does not verify your key,
subscription, or model availability.

## Uninstall

```sh
rm -- "$HOME/.local/bin/codex-aicheap" "${CODEX_HOME:-$HOME/.codex}/aicheap-api-key"
```

The Codex CLI itself is left installed.

## Checks

Tests use an isolated home directory, fake credentials, and mocked Codex/npm.
They make no network calls or paid API requests.

```sh
bash -n setup-codex.sh
python3 -m unittest discover -s tests -v
```
