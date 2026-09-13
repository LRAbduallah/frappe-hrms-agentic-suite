# Frappe HRMS Agentic Suite

An AI-powered HR operations platform that connects a web UI and an
OpenAI-compatible agent API to Frappe HRMS through Model Context Protocol (MCP).
Frappe remains the system of record for HR data, permissions, workflows, and
audit history.

## Start the complete stack

```bash
cp .env.example .env
# Replace every replace-with-* value in .env
docker compose up -d --build
```

Open the UI at [http://localhost:8080](http://localhost:8080).

## Documentation

The documentation is centralized under [`docs/`](docs/README.md):

| Guide | Purpose |
| --- | --- |
| [Documentation index](docs/README.md) | Entry point and guide map |
| [Architecture](docs/architecture.md) | Components, boundaries, diagrams, and request flows |
| [Services](docs/services.md) | Responsibilities, ports, APIs, and source layout |
| [Deployment](docs/deployment.md) | Docker setup, environment, operations, and hardening |
| [Development](docs/development.md) | Local development, builds, smoke tests, and troubleshooting |
| [MCP integration](docs/mcp.md) | Tools, transports, permissions, and Frappe data flows |

Component directories contain only short pointers back to these canonical
guides:

- [`mcp/README.md`](mcp/README.md)
- [`hr-agent/README.md`](hr-agent/README.md)
- [`hr-agent-ui/README.md`](hr-agent-ui/README.md)

## Repository map

```text
.
├── docker-compose.yml       # Complete multi-service deployment
├── docs/                    # Canonical project documentation
├── hr-agent/                # FastAPI + Strands orchestration service
├── hr-agent-ui/             # React/Vite web application
└── mcp/                    # Frappe HRMS MCP server and local Frappe bootstrap
```

For the system mental model, start with [Architecture](docs/architecture.md).
