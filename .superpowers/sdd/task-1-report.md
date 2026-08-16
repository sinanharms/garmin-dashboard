# Task 1 Report: Validated Configuration and Container Workflow

## Status

DONE for the requested implementation. The application configuration, dependency metadata, container workflow, tests, documentation, and repository guidance are committed.

## Commit

- `7a4ce9d build: add Garmin dashboard runtime configuration`

Only the nine Task 1 implementation paths were staged and committed:

- `.dockerignore`
- `AGENTS.md`
- `Dockerfile`
- `README.md`
- `compose.yaml`
- `pyproject.toml`
- `src/strava_dashboard/config.py`
- `tests/test_config.py`
- `uv.lock`

Existing unrelated untracked files remain unstaged.

## Implementation

- Added the required runtime dependencies and regenerated `uv.lock` with `uv lock`.
- Renamed the project description and README to Garmin training dashboard terminology.
- Added `Settings` with explicit environment aliases, required values, positive integer validation, forbidden extras, and a redacted `SecretStr` password.
- Added focused tests for environment loading, secret redaction, missing credentials, empty passwords, and extra settings.
- Added a Python 3.14 slim image that installs the locked application and both Garmin MCP commands at build time.
- Added `app` and `scheduler` Compose services sharing named dashboard/token volumes, with web access bound only to `127.0.0.1:8000`.
- Added Docker ignore rules and documented `.env` creation without exposing values.
- Added repository-specific Docker-first workflow guidance in `AGENTS.md`.

## Verification

- Focused tests: `uv run pytest tests/test_config.py -q` — 4 passed.
- Full tests: `uv run pytest -q` — 5 passed.
- Ruff lint: passed.
- Ruff format check: passed.
- Direct type check: `uv run ty check --python .venv/bin/python` — passed.
- Pre-commit checks: passed except the isolated `ty` hook, which was skipped at commit time because its environment could not resolve project dependencies. The project `uv run ty` check passed directly.
- `git diff --check`: passed.

## Concern

Docker checks could not execute because the environment has no `docker` executable (`Failed to spawn process: No such file or directory`). Therefore `docker compose config` and the image build were not runnable here. The Compose file was still checked by the repository pre-commit YAML hook, and no `garmin-mcp` HTTP service or non-loopback port publishing is defined.

## Fix: Task 1 Review Findings

### Changes

- Set container `HOME` to `/root` and default `GARMIN_TOKEN_DIR` to `/root/.garminconnect` in `Dockerfile`.
- Updated both Compose services to set `GARMIN_TOKEN_DIR=/root/.garminconnect` and mount `garmin_tokens` at `/root/.garminconnect`, matching Garmin MCP authentication and runtime MCP state under root's persisted home directory.
- Documented all required environment variable names in `README.md` without values.

### Verification

- `rtk env UV_CACHE_DIR=/private/tmp/strava-dashboard-uv-cache uv run pytest tests/test_config.py -q` — `4 passed in 0.09s`.
- `rtk ruby -e 'require "yaml"; YAML.load_file("compose.yaml"); puts "compose.yaml: valid YAML"'` — `compose.yaml: valid YAML`.
- `rtk rg -n 'HOME|GARMIN_TOKEN_DIR|garmin_tokens|/root/.garminconnect' Dockerfile compose.yaml README.md` — confirmed `HOME=/root`, `GARMIN_TOKEN_DIR=/root/.garminconnect`, and both volume mounts at `/root/.garminconnect`.
- `rtk git diff --check` — passed.
- `rtk docker compose run --rm app uv run pytest tests/test_config.py -q` — not runnable: `docker` executable unavailable.
- `rtk docker compose config` — not runnable: `docker` executable unavailable.
