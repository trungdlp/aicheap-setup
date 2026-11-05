#!/usr/bin/env bash
# macOS/Linux entry point; the shared installer also runs on native Windows.
set +x
set -euo pipefail

setup_python=''
for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
  if command -v "$candidate" >/dev/null 2>&1 &&
      "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    setup_python="$candidate"
    break
  fi
done
[[ -n "$setup_python" ]] || {
  printf 'Install Python 3.11 or newer, then rerun setup.\n' >&2
  exit 1
}

installer="$(cd "$(dirname "$0")" && pwd)/setup-codex.py"
if [[ -f "$installer" ]]; then
  exec "$setup_python" "$installer" "$@"
fi

# Keep the existing single-file download command working.
installer="$(mktemp)"
trap 'rm -f -- "$installer"' EXIT
curl -fsSL https://raw.githubusercontent.com/trungdlp/aicheap-setup/HEAD/setup-codex.py -o "$installer"
"$setup_python" "$installer" "$@"
