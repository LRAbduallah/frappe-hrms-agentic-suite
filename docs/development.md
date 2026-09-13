# Development guide

## Prerequisites

- Python 3.12+
- Node.js 22+
- npm
- Docker Desktop with Compose v2 for the integrated stack

## Run the integrated stack

Use the root instructions in [Deployment](deployment.md). This is the closest
environment to the production topology and is the preferred way to test
cross-service behavior.

## Run the UI locally

```bash
cd hr-agent-ui
npm ci
cp .env.example .env
npm run dev
```

The Vite server runs on `http://localhost:5173` and proxies `/v1`, `/health`,
and `/ready` to `http://localhost:8001`.

For a production bundle:

```bash
npm run build
npm run lint
```

## Run the agent locally

```bash
cd hr-agent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Set `FRAPPE_MCP_URL` to a reachable MCP endpoint. For the integrated Docker
stack, use `http://mcp-gateway:8800/mcp` from inside Docker or
`http://localhost:8800/mcp` from the host.

## Run the MCP server locally

```bash
cd mcp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --http --mode production --port 8800
```

For desktop MCP clients, use stdio:

```bash
.venv/bin/python run.py --mode production
```

See [MCP integration](mcp.md) for credentials, tool modes, and client
configuration.

## Validation checklist

```bash
# Compose syntax and interpolation
docker compose --env-file .env.example config --quiet

# UI
npm --prefix hr-agent-ui run build
npm --prefix hr-agent-ui run lint

# Service health
curl http://localhost:8001/health
curl http://localhost:8001/ready
curl http://localhost:8080
```

For MCP smoke tests, use the read-only sequence documented in
[MCP integration](mcp.md).

## Troubleshooting

### Agent starts but MCP tools are unavailable

Check `FRAPPE_MCP_URL`, `MCP_BEARER_TOKEN`, gateway logs, and the MCP server
logs. The agent can start in an offline state, but Frappe-backed actions will
not work until discovery succeeds.

### Frappe does not start

Follow the bootstrap logs:

```bash
docker compose logs -f frappe
```

The first initialization is slow. If a bootstrap was interrupted and the
volume is unusable, remove only the named volumes after confirming that the
data can be discarded.

### CORS or browser API errors

Use the default empty `VITE_API_BASE_URL` with the production Nginx proxy. For
an external API origin, configure the URL and the deployment's CORS policy
deliberately.
