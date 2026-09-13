# Frappe HR Operations Agent (Strands Agents SDK + Frappe HRMS MCP)

An intelligent, multi-agent HR operations system built with the **Strands Agents SDK** (`strands-agents`) and integrated with **Frappe HRMS** via **Model Context Protocol (MCP)**.

The system exposes an **OpenAI-compatible API** (`/v1/chat/completions`, `/v1/models`) so it seamlessly connects to ChatGPT-style frontends such as NextChat, OpenWebUI, Big-AGI, or custom applications.

---

## 1. Architecture

```text
                    ┌─────────────────────────┐
                    │  Chat UI / OpenWebUI    │
                    └───────────┬─────────────┘
                                │ OpenAI-Compatible /v1/chat/completions
                                ▼
                    ┌─────────────────────────┐
                    │      FastAPI App        │
                    │   (Strands Orchestrator)│
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   Employee   │        │ Leave & Att. │        │  Reporting   │
│  Specialist  │        │  Specialist  │        │  Specialist  │
└───────┬──────┘        └───────┬──────┘        └───────┬──────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │       Frappe MCP        │
                    │      (Streamable)       │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │       Frappe HRMS       │
                    └─────────────────────────┘
```

- **Intelligence Layer**: Strands Agents (`strands-agents`) with multi-agent delegation via `agent.as_tool()`.
- **Integration Layer**: Native Model Context Protocol (MCP) streamable HTTP client connecting to `FRAPPE_MCP_URL`.
- **Governance**: Human-in-the-Loop (HITL) approval framework. Dangerous mutations require structured approvals (`/v1/approvals`).
- **Observability**: Strands Hook system (`HRAgentGovernanceHook`) tracking invocations, tool arguments, and latency.

---

## 2. Universal Model Provider Compatibility

Configured exclusively through environment variables (`.env`). Supports any OpenAI-compatible provider:
- **Official OpenAI**: `OPENAI_MODEL=gpt-4o-mini`, `OPENAI_API_KEY=sk-...`
- **Mistral**: `OPENAI_BASE_URL=https://api.mistral.ai/v1`, `OPENAI_MODEL=mistral-large-latest`
- **Ollama**: `OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_MODEL=llama3.1`
- **LM Studio**: `OPENAI_BASE_URL=http://localhost:1234/v1`, `OPENAI_MODEL=local-model`
- **OpenRouter / Groq / vLLM / DeepSeek**

---

## 3. Quick Start

### Step 1: Virtual Environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to set your `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, and `FRAPPE_MCP_URL`.

### Step 3: Run the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 4. API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/v1/chat/completions` | `POST` | OpenAI-compatible chat completion (supports streaming) |
| `/v1/models` | `GET` | Lists available models |
| `/v1/approvals` | `GET` | List pending mutation proposals |
| `/v1/approvals/{id}/approve` | `POST` | Approve and execute mutation |
| `/v1/approvals/{id}/reject` | `POST` | Reject proposed mutation |
| `/health` | `GET` | Process liveness check |
| `/ready` | `GET` | Readiness probe (checks MCP and model configuration) |

---

## 5. Docker Deployment

Build and run standalone:
```bash
docker build -t strands-hr-agent .
docker run -p 8001:8001 --env-file .env strands-hr-agent
```

Or run within the Frappe Docker Compose stack:
```yaml
strands-api:
  build:
    context: ./hr-agent
    dockerfile: Dockerfile
  environment:
    FRAPPE_MCP_URL: http://mcp-gateway:8800/mcp
  ports:
    - "8001:8001"
```
