# Documentation

This is the canonical documentation for the Frappe HRMS Agentic Suite. Start
with the architecture guide, then use the deployment or development guide
depending on how you are running the system.

## Guides

| Guide | When to read it |
| --- | --- |
| [Architecture](architecture.md) | Understand what each service does and how a request moves through the system |
| [Services](services.md) | Find ports, endpoints, source directories, and ownership boundaries |
| [Deployment](deployment.md) | Run the complete Docker Compose stack and operate it safely |
| [Development](development.md) | Run one service locally, build the UI, and debug changes |
| [MCP integration](mcp.md) | Configure Frappe credentials, MCP transports, tools, and permissions |

## Quick links

- Root environment template: [`../.env.example`](../.env.example)
- Compose deployment: [`../docker-compose.yml`](../docker-compose.yml)
- UI source: [`../hr-agent-ui/`](../hr-agent-ui/)
- Agent source: [`../hr-agent/`](../hr-agent/)
- MCP source: [`../mcp/`](../mcp/)

## Recommended reading order

1. [Architecture](architecture.md)
2. [Services](services.md)
3. [MCP integration](mcp.md)
4. [Deployment](deployment.md) or [Development](development.md)
