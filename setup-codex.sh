#!/usr/bin/env bash
# Install a separate AI Cheap launcher without changing the default Codex setup.
set +x
set -euo pipefail
umask 077

if [[ $# -ne 0 ]]; then
  printf 'Usage: bash setup-codex.sh (no arguments; API key is prompted)\n' >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  if ! command -v npm >/dev/null 2>&1; then
    printf 'Install Node.js with npm first, then rerun this script.\n' >&2
    exit 1
  fi
  npm install -g @openai/codex
  command -v codex >/dev/null 2>&1 || {
    printf 'Add the npm global bin directory to PATH, then rerun this script.\n' >&2
    exit 1
  }
fi

codex_dir="${CODEX_HOME:-$HOME/.codex}"
bin_dir="$HOME/.local/bin"
key_file="$codex_dir/aicheap-api-key"
mkdir -p "$codex_dir" "$bin_dir"

if [[ -z "${AICHEAP_API_KEY:-}" && ! -s "$key_file" ]]; then
  printf 'Create an API key at https://console.aicheap.io/\n' >&2
  if ! read -r -s -p 'AI Cheap API key: ' AICHEAP_API_KEY </dev/tty; then
    printf '\nNo key read. For automation, supply AICHEAP_API_KEY in the environment.\n' >&2
    exit 1
  fi
  printf '\n' >&2
fi

key_tmp=''
launcher_tmp=''
trap 'rm -f -- "${key_tmp:-}" "${launcher_tmp:-}"' EXIT
if [[ -n "${AICHEAP_API_KEY:-}" ]]; then
  if [[ "$AICHEAP_API_KEY" == *[[:space:]]* ]]; then
    printf 'API key must not contain whitespace.\n' >&2
    exit 1
  fi
  key_tmp="$(mktemp "$codex_dir/.aicheap-key.XXXXXX")"
  printf '%s' "$AICHEAP_API_KEY" > "$key_tmp"
  mv -f -- "$key_tmp" "$key_file"
fi
[[ -s "$key_file" ]] || { printf 'An API key is required.\n' >&2; exit 1; }
chmod 600 "$key_file"
unset AICHEAP_API_KEY

launcher_tmp="$(mktemp "$bin_dir/.codex-aicheap.XXXXXX")"
cat > "$launcher_tmp" <<'LAUNCHER'
#!/usr/bin/env bash
set +x
set -euo pipefail

if [[ -z "${AICHEAP_API_KEY:-}" ]]; then
  key_file="${CODEX_HOME:-$HOME/.codex}/aicheap-api-key"
  [[ -s "$key_file" ]] || {
    printf 'AI Cheap key missing; rerun setup-codex.sh.\n' >&2
    exit 1
  }
  AICHEAP_API_KEY="$(< "$key_file")"
fi
export AICHEAP_API_KEY

exec codex \
  -c 'model_provider="aicheap"' \
  -c 'model="GPT-6.1-Sol"' \
  -c 'model_providers.aicheap={name="AI Cheap",base_url="https://api.aicheap.io/openai/v1",env_key="AICHEAP_API_KEY",wire_api="responses"}' \
  "$@"
LAUNCHER
chmod 700 "$launcher_tmp"
mv -f -- "$launcher_tmp" "$bin_dir/codex-aicheap"
printf 'Installed %s/codex-aicheap\n' "$bin_dir"
printf 'Run: "%s/codex-aicheap"\n' "$bin_dir"
printf 'To use the short command, ensure %s is on PATH.\n' "$bin_dir"
