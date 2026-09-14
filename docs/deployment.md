# Docker deployment

The repository-root `docker-compose.yml` runs the complete suite:

```text
UI (Nginx) -> Strands HR agent -> MCP gateway -> MCP server -> Frappe
                                                        -> MariaDB
                                                        -> Redis
```

## First run

1. Install Docker Engine or Docker Desktop with Compose v2.
2. Create the environment file and replace every `replace-with-*` value:

   ```bash
   cp .env.example .env
   chmod 600 .env
   ```

3. Create a dedicated Frappe API user with only the HRMS permissions required by
   the agent. Put its API key and secret in `.env`.
4. Start from the repository root:

   ```bash
   docker compose up -d --build --wait
   docker compose ps
   ```

5. Open `http://localhost:8080`. The API is available at `http://localhost:8001`
   and the authenticated MCP endpoint is `http://localhost:8800/mcp`.

The first Frappe startup downloads ERPNext and HRMS and may take several
minutes. Data is stored in named Docker volumes.

## Environment

The root [`.env.example`](../.env.example) is the canonical environment
template. Runtime secrets stay in `.env`, which is ignored by Git.

Required values:

| Variable | Used by |
| --- | --- |
| `MARIADB_ROOT_PASSWORD` | MariaDB and first Frappe site initialization |
| `FRAPPE_ADMIN_PASSWORD` | First Frappe Administrator password |
| `FRAPPE_API_KEY` / `FRAPPE_API_SECRET` | MCP-to-Frappe authentication |
| `MCP_BEARER_TOKEN` | Agent-to-MCP gateway authentication |
| `OPENAI_API_KEY` | Configured model provider |

The Frappe bootstrap credentials only apply when the persistent Frappe volume is
initialized for the first time. Changing them later does not change existing
database credentials.

The leave workflow uses the same OpenAI-compatible provider as `strands-api`,
the same MariaDB container, but a separate database and user. Set
`OPENAI_MODEL`, `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`,
`STRANDS_DB_PASSWORD`, and `STRANDS_WORKFLOW_PORT`
in `.env`. `strands-db-init` creates the database before
`strands-hr-workflow` runs Alembic migrations. The workflow is ready only after
the database is reachable and the authenticated MCP gateway exposes
`hrms_find_employee` and `hrms_get_leave_balance`.

## UI networking

The UI uses an empty `VITE_API_BASE_URL` by default. Nginx proxies `/v1`,
`/health`, and `/ready` to `strands-api`, so browser traffic remains
same-origin. Rebuild the UI after changing `VITE_*` values:

```bash
docker compose build --no-cache ui
docker compose up -d ui
```

## Operations

```bash
docker compose logs -f strands-api
docker compose logs -f strands-hr-workflow
docker compose ps
docker compose pull
docker compose build
docker compose up -d
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete
MariaDB, Frappe, and agent data.

## Production hardening

- Terminate HTTPS at an external reverse proxy.
- Restrict or remove host mappings for ports 8000, 8001, and 8800 if only the
  UI should be public.
- Store `.env` in a secret manager and rotate API credentials.
- Back up `mariadb-data`, `frappe-home-data`, and `agent-data`.
- Pin image tags or digests through an approved update process.
- Keep MCP in production mode and `BYPASS_TOOL_CONSENT=false`.
- Monitor health endpoints, container restarts, Frappe logs, and model provider
  failures.
