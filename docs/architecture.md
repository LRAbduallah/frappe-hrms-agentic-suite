# Architecture and system flows

## What the system is

The suite is an orchestration layer around Frappe HRMS. It does not maintain a
second HR database. The browser talks to the HR agent API, the agent discovers
and calls MCP tools, and the MCP server calls Frappe's REST and RPC APIs.

```mermaid
flowchart LR
    User[HR user] --> UI[React UI]
    UI -->|/v1/chat/completions| Agent[FastAPI HR agent]
    Agent -->|model reasoning| LLM[OpenAI-compatible provider]
    Agent -->|Streamable HTTP| Gateway[MCP gateway]
    Gateway --> MCP[Frappe HR MCP server]
    MCP -->|token API auth| Frappe[Frappe HRMS]
    Frappe --> DB[(MariaDB)]
    Frappe --> Redis[(Redis)]
```

## Production Compose topology

```mermaid
graph TD
    subgraph Public["Host-facing services"]
        UI["ui<br/>Nginx + React<br/>:8080"]
        API["strands-api<br/>FastAPI<br/>:8001"]
        MCPHTTP["mcp-gateway<br/>Nginx auth proxy<br/>:8800"]
        FrappeHTTP["frappe<br/>Bench<br/>:8000"]
    end

    subgraph Internal["Docker network: frappe-network"]
        MCP["mcp<br/>Python MCP server"]
        MariaDB["mariadb<br/>persistent volume"]
        Redis["redis"]
    end

    UI --> API
    API --> MCPHTTP
    MCPHTTP --> MCP
    MCP --> FrappeHTTP
    FrappeHTTP --> MariaDB
    FrappeHTTP --> Redis
```

The host mappings are configurable. In a hardened deployment, expose only the
UI through an external reverse proxy and keep the API, MCP, and Frappe mappings
private.

## Request flow: chat and tool use

```mermaid
sequenceDiagram
    participant Browser
    participant UI as React UI
    participant Agent as Strands FastAPI
    participant Model as LLM provider
    participant Gateway as MCP gateway
    participant MCP as MCP server
    participant Frappe as Frappe HRMS

    Browser->>UI: Enter HR request
    UI->>Agent: POST /v1/chat/completions
    Agent->>Model: Reason over request and available tools
    Agent->>Gateway: MCP tool call + bearer token
    Gateway->>MCP: Authenticated Streamable HTTP
    MCP->>Frappe: REST resource or whitelisted RPC
    Frappe-->>MCP: Data, validation, or permission result
    MCP-->>Gateway: Structured tool result
    Gateway-->>Agent: Tool result
    Agent-->>UI: JSON or SSE response
    UI-->>Browser: Render answer and status
```

## Request flow: approved mutation

Writes are governed by the agent's approval layer when HITL is enabled.

```mermaid
flowchart TD
    Intent[User asks for a change] --> Plan[Agent proposes a tool call]
    Plan --> DryRun[Pre-flight validation / dry run]
    DryRun --> Review{HITL approval required?}
    Review -->|Yes| Pending[Pending approval in agent storage]
    Pending --> Decision{User approves?}
    Decision -->|No| Reject[Reject and record decision]
    Decision -->|Yes| Execute[Execute MCP mutation]
    Review -->|No| Execute
    Execute --> Frappe[Frappe validates permissions and workflow]
    Frappe --> Result[Return result and update session]
```

Frappe is still the final authority. Agent approval does not bypass Frappe
permissions, mandatory fields, document state, or workflow rules.

## Service responsibilities

| Layer | Responsibility | Does not own |
| --- | --- | --- |
| UI | Chat, approvals, sessions, health display | Model credentials or HR persistence |
| HR agent | Orchestration, specialist selection, streaming API, HITL | Frappe authorization or database |
| MCP gateway | Network boundary and bearer-token check | Frappe business logic |
| MCP server | Tool registration, input validation, Frappe client calls | Agent reasoning |
| Frappe HRMS | HR records, permissions, validation, workflows, audit history | LLM behavior |
| MariaDB/Redis | Frappe persistence and runtime services | Agent session semantics |

## Important boundaries and fallbacks

- `FRAPPE_MCP_MODE=production` omits destructive delete and bulk-create tools.
- `admin` mode exposes additional tools but does not grant Frappe permissions.
- The agent can start when MCP is temporarily unavailable, but tool-backed
  operations are not reliable until the MCP connection is restored.
- There is no local transaction or rollback across multiple Frappe API calls.
- Bulk operations are sequential and can leave partial results.
- Frappe API credentials belong to the MCP server, not the browser.

## Typical leave request

```mermaid
flowchart LR
    A[User: apply leave] --> B[hrms_find_employee]
    B --> C[frappe_get_link_options<br/>Leave Type]
    C --> D[hrms_apply_leave]
    D --> E{Submission required?}
    E -->|Yes| F[frappe_submit_document]
    E -->|No| G[Leave remains open/draft]
    F --> H[frappe_get_document]
    G --> H
```

`hrms_apply_leave` creates the Leave Application. Submission is a separate,
deliberate workflow operation.
