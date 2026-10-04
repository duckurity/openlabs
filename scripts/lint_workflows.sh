#!/usr/bin/env bash
# Validate GitHub Actions workflow files with actionlint.
#
# Install actionlint v1.7.7 from:
#   https://github.com/rhysd/actionlint/releases/tag/v1.7.7
# Verify the linux_amd64 tarball against checksums.txt in that release.
#
# Usage:
#   bash scripts/lint_workflows.sh

set -euo pipefail

if ! command -v actionlint >/dev/null 2>&1; then
  echo "scripts/lint_workflows.sh: actionlint not found in PATH." >&2
  echo "Install release v1.7.7 from https://github.com/rhysd/actionlint/releases/tag/v1.7.7" >&2
  echo "and verify the tarball with actionlint_1.7.7_checksums.txt from the same release." >&2
  exit 127
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
shopt -s nullglob
files=("${ROOT}/.github/workflows/"*.yml)
if ((${#files[@]} == 0)); then
  echo "scripts/lint_workflows.sh: no workflow files under .github/workflows/" >&2
  exit 1
fi

actionlint -color "${files[@]}"
