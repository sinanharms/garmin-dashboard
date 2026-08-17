#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${GARMIN_EMAIL:-}" ]]; then
  :
else
  printf '%s\n' 'GARMIN_EMAIL is required' >&2
  exit 1
fi
if [[ -n "${GARMIN_PASSWORD:-}" ]]; then
  :
else
  printf '%s\n' 'GARMIN_PASSWORD is required' >&2
  exit 1
fi

exec uvx --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth
