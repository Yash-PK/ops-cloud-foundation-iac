#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
printf '%s\n' 'Mock-only AWS foundation: no credentials, API calls, state backend or resources.'
.venv/bin/python scripts/iac.py test
printf '%s\n' 'Unsafe copies of actual mock plans were rejected in memory; source stayed unchanged.'
printf '%s\n' 'Recovery: original plans still pass. No destructive fault or cloud cleanup is needed.'
if .venv/bin/python scripts/iac.py apply; then
  printf '%s\n' 'ERROR: unauthorized apply was accepted' >&2
  exit 1
else
  code=$?
  if [[ "$code" -ne 3 ]]; then
    printf 'Unexpected refusal exit code: %s\n' "$code" >&2
    exit 1
  fi
fi
printf '%s\n' 'Live apply refusal: expected exit 3. Actual AWS reachability and IAM remain unverified.'
