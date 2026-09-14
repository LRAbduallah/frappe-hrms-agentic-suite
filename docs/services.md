# Services and code map

## Runtime services

| Compose service | Purpose | Default host port | Main source |
| --- | --- | ---: | --- |
| `ui` | React production bundle and same-origin Nginx proxy | 8080 | `hr-agent-ui/` |
| `strands-api` | OpenAI-compatible FastAPI API and agent orchestration | 8001 | `hr-agent/` |
| `strands-hr-workflow` | Mistral leave workflow, audit API, and mock email callback | 8002 | `strands-hr-workflow/` |
| `strands-db-init` | Creates the workflow database and least-privilege user | none | `strands-hr-workflow/app/database/bootstrap.py` |
| `mcp-gateway` | Nginx bearer-token boundary for MCP HTTP | 8800 | `mcp/docker/nginx.conf.template` |
| `mcp` | MCP tool server for Frappe HRMS | internal 8800 | `mcp/run.py`, `mcp/mcpp/` |
| `frappe` | Frappe Bench with ERPNext and HRMS | 8000 | `mcp/docker/init.sh` |
| `mariadb` | Frappe database | internal 3306 | Docker image |
| `redis` | Frappe cache, queue, and socket service | internal 6379 | Docker image |

## Agent API

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/v1/chat/completions` | POST | OpenAI-compatible chat request; supports streaming |
| `/v1/models` | GET | Lists `hr-agent` and configured model |
| `/v1/approvals` | GET | Lists pending mutation approvals |
| `/v1/approvals/{id}/approve` | POST | Approves and executes a mutation |
| `/v1/approvals/{id}/reject` | POST | Rejects a mutation |
| `/v1/approvals/{id}/dry-run` | POST | Runs pre-flight validation |
| `/v1/sessions` | GET/POST | Lists and creates chat sessions |
| `/health` | GET | Liveness check |
| `/ready` | GET | Model and MCP readiness |

## Agent internals

| Path | Responsibility |
| --- | --- |
| `hr-agent/app/main.py` | FastAPI app, lifespan, routers, CORS |
| `hr-agent/app/config.py` | Environment-backed settings |
| `hr-agent/app/api/chat.py` | Chat completions and model listing |
| `hr-agent/app/api/approvals.py` | Approval execution endpoints |
| `hr-agent/app/api/sessions.py` | Session persistence endpoints |
| `hr-agent/app/agents/orchestrator.py` | Main Strands agent |
| `hr-agent/app/agents/specialists.py` | Domain specialist agents |
| `hr-agent/app/mcp/manager.py` | MCP connection and tool discovery |
| `hr-agent/app/governance/` | HITL, dry-run, and payload validation |
| `hr-agent/app/hooks/` | Agent governance and observability hooks |

## MCP internals

| Path | Responsibility |
| --- | --- |
| `mcp/run.py` | CLI and stdio/Streamable HTTP startup |
| `mcp/mcpp/server.py` | MCP server construction and tool registration |
| `mcp/mcpp/client.py` | Frappe REST/RPC client |
| `mcp/mcpp/config.py` | MCP environment configuration |
| `mcp/mcpp/tools/discovery.py` | DocType and schema discovery |
| `mcp/mcpp/tools/documents.py` | Generic CRUD operations |
| `mcp/mcpp/tools/workflow.py` | Submit, cancel, and timeline operations |
| `mcp/mcpp/tools/entity/` | Leave, attendance, payroll, and lifecycle tools |
| `mcp/mcpp/tools/schema.py` | Pydantic input validation |
| `mcp/mcpp/doctypes.py` | Curated HRMS DocType registry |

## UI internals

| Path | Responsibility |
| --- | --- |
| `hr-agent-ui/src/App.jsx` | Application shell and service status |
| `hr-agent-ui/src/api.js` | Agent API client |
| `hr-agent-ui/src/components/ChatInterface.jsx` | Chat and streaming UI |
| `hr-agent-ui/src/components/ApprovalsPanel.jsx` | Mutation approval UI |
| `hr-agent-ui/src/components/Sidebar.jsx` | Sessions and navigation |
| `hr-agent-ui/vite.config.js` | Local development proxy |
| `hr-agent-ui/Dockerfile` | Production build and Nginx image |

## Data and storage

| Data | Location | Owner |
| --- | --- | --- |
| HR records and Frappe metadata | `mariadb-data` volume | Frappe/MariaDB |
| Frappe bench, sites, and files | `frappe-home-data` volume | Frappe |
| Agent sessions and approvals | `agent-data` volume | HR agent |
| Browser build configuration | `VITE_*` build arguments | UI image |

The UI must never receive `OPENAI_API_KEY`, Frappe API credentials, or the MCP
bearer token.

## Leave workflow API

The migrated workflow exposes the imported FastAPI routes on port `8002`,
including `POST /workflows/trigger`, `GET /health`, and dependency-aware
`GET /ready`. It calls `http://mcp-gateway:8800/mcp` with the shared bearer
token and stores Alembic tables in the dedicated `STRANDS_DB_NAME` database on
the shared MariaDB service. The imported `/leaves/send_email` route remains a
mock queue callback for this migration.
