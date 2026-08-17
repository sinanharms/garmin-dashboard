# Convention: security and secrets

## Runtime boundary

The service is intended for local access. Compose publishes FastAPI only at `127.0.0.1:8000`; the scheduler and Garmin MCP child process have no published ports. Do not add public hosting, remote access, or an HTTP MCP endpoint without a new decision.

## Secret handling

- Keep Garmin credentials in local `.env` or an external secret manager; never commit or print values.
- `GARMIN_PASSWORD` is loaded as Pydantic `SecretStr`.
- Persist Garmin authentication state only in the protected `garmin_tokens` volume.
- Never copy token state, raw MCP responses, prompts, API keys, or credentials into the repository.
- Never expose arbitrary SQL or arbitrary MCP tool calls through HTTP.

## Response and error redaction

FastAPI maps storage exceptions to `{"detail":"storage unavailable"}` and unexpected exceptions to `{"detail":"internal server error"}`. API diagnostics expose operator-safe statuses and error codes, not exception text, local secret paths, token contents, prompts, or raw MCP data.

## Documentation rule

Examples use placeholders such as `BACKUP_ID.sqlite3.gz`. They must not include real credentials, token values, local secret paths, or raw external payloads.

Applies to [Garmin synchronization](../stories/garmin-sync.md), [dashboard and trends](../stories/dashboard-and-trends.md), [planning and coaching](../stories/planning-and-coaching.md), [operations and backups](../stories/operations-and-backups.md), and the planned [React dashboard](../stories/react-dashboard.md).
