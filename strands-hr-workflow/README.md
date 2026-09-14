# Strands HR Workflow

This application is integrated into the parent `frappe-hrms-agentic-suite`
Compose stack as the `strands-hr-workflow` service. Run it from the parent
directory so Compose supplies the MariaDB, MCP gateway, and callback URLs.

```bash
docker compose up -d --build --wait
docker compose exec strands-hr-workflow \
  python app/agentic_workflow/leave_agent.py
```

The service uses `http://mcp-gateway:8800/mcp` for authenticated MCP access and
stores its Alembic-managed tables in the dedicated workflow database created by
`strands-db-init`. Existing Frappe employee and leave data is required.

This repository is an HR Management System built with Strands Agents. Leave
management is the current scope. The leave agent reads employee
leave balances through a Frappe HRMS MCP server, drafts leave emails with
Mistral, and sends or queues those emails for human review. Additional HR
management capabilities can be added to the same application as the scope
expands.

## Prerequisites

- Python 3.10 or newer
- A running Frappe HRMS instance
- The Frappe HRMS MCP server checked out locally and configured to access that
  Frappe instance
- A Mistral API key

Before starting the agent, complete these prerequisite steps in order:

1. Create or select a Frappe user for the MCP integration.
2. Generate an API key and API secret for that Frappe user.
3. Add the Frappe URL and generated credentials to the MCP server's `.env`.
4. Add the Mistral key and MCP URL to this repository's `.env`.
5. Initialize the SQLite database with the Alembic migration.
6. Start Frappe, the MCP server, and this repository's API.

## Create Frappe API credentials

The MCP server accesses Frappe on behalf of a Frappe user. Create a dedicated
integration user when possible, rather than using a personal administrator
account.

1. Sign in to the Frappe HRMS site as a user who can manage users.
2. Open **User** from the Desk search or the Users list.
3. Create a new user, or open an existing integration user.
4. Give the user the HRMS roles and DocType permissions required to read
  employees and leave balances. The user must be able to access the Employee
  and leave-related DocTypes used by the MCP tools.
5. In the user's **API Access** section, choose **Generate Keys** or the
  equivalent API-key action available in your Frappe version.
6. Copy the generated **API Key** and **API Secret** immediately. The secret
  may only be shown once. If it is lost, generate a new key pair.

Use the generated values in the MCP server configuration as follows:

```dotenv
FRAPPE_BASE_URL=http://localhost:8000
FRAPPE_API_KEY=<api-key-generated-for-the-frappe-user>
FRAPPE_API_SECRET=<api-secret-generated-for-the-frappe-user>
```

Do not use the Mistral key as the Frappe API key. They are separate credentials:
the Frappe key authenticates the MCP server to Frappe, while the Mistral key
authenticates the agent's language-model requests.

The workflow uses three local services:

| Service | Default URL | Purpose |
| --- | --- | --- |
| Frappe HRMS | `http://localhost:8000` | Employee and leave data |
| Frappe MCP server | `http://localhost:8800/mcp` | Streamable HTTP MCP endpoint |
| This repository's API | `http://127.0.0.1:8001` | Mock leave email API and workflow API |

Run the repository API on port `8001`. Frappe normally uses port `8000`, and
using the same port for both services will prevent one of them from starting.

## Clone and install

From the repository root:

```bash
git clone <repository-url>
cd Strands-for-HR-Management-System

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, the included script can also use the virtual environment
directly with `.venv/bin/python`.

## Configure the Frappe MCP server

The Frappe URL and Frappe API credentials belong to the **MCP server's
configuration**, not to the Strands agent itself. In the MCP server repository,
create or update its `.env` file with values like these:

```dotenv
FRAPPE_BASE_URL=http://localhost:8000
FRAPPE_API_KEY=<frappe-api-key>
FRAPPE_API_SECRET=<frappe-api-secret>
FRAPPE_MCP_MODE=production
FRAPPE_REQUEST_TIMEOUT=30
```

Replace all placeholder values with the Frappe URL and API key pair generated
in the previous section. Use the minimum permissions needed by the HRMS MCP
tools. Do not commit this file or put real credentials in this README.

Start the MCP server from its own repository root. The command documented by
this project is:

```bash
.venv/bin/python run.py --http --mode production --port 8800
```

If the MCP repository uses a different virtual environment path, replace
`.venv/bin/python` with that environment's Python executable. Confirm that the
server is listening at:

```text
http://localhost:8800/mcp
```

## Configure this application

Create `.env` in this repository root. The application loads this exact file
when `app.configuration.config.get_settings()` is called.

```dotenv
# Required by the Strands Mistral model
MISTRAL_API_KEY=<mistral-api-key>

# MCP endpoint exposed by the Frappe MCP server
FRAPPE_MCP_URL=http://localhost:8800/mcp

# SQLite database and workflow cooldown
DATABASE_URL=sqlite:///data/hr_management.db
WORKFLOW_COOLDOWN_DAYS=15

# Optional employee search and workflow settings
MCP_EMPLOYEE_QUERY=*
LOW_LEAVE_THRESHOLD_DAYS=2.0
LOW_LEAVE_THRESHOLD_RATIO=0.15
HITL_ENABLED=true
BYPASS_TOOL_CONSENT=true

# This repository's FastAPI email endpoint. Keep this on port 8001 when
# Frappe is running on port 8000.
EMAIL_API_BASE_URL=http://127.0.0.1:8001
```

At minimum, replace `<mistral-api-key>` with a valid Mistral API key. The
Frappe API key and secret do not belong in this file; they belong in the MCP
server's `.env` shown above. Keep the application `.env` in the repository
root, next to `requirements.txt`.

`FRAPPE_BASE_URL`, `FRAPPE_API_KEY`, and `FRAPPE_API_SECRET` are intentionally
not used by this application. They must be configured in the MCP server as
shown above. This application connects to Frappe indirectly through
`FRAPPE_MCP_URL`.

## Initialize the database

The application stores workflow runs and per-email audit events in SQLite. The
default database is `data/hr_management.db`, and `DATABASE_URL` can override
that location. Run the migration after installing dependencies and before
starting the API or leave agent:

```bash
alembic upgrade head
```

`WORKFLOW_COOLDOWN_DAYS` controls repeat workflow execution. Set it to `0` to
allow every run. The example value `15` allows a new leave
workflow only after 15 full days have elapsed since the latest completed leave
workflow. A blocked trigger is recorded in the database with status `blocked`,
and it does not call the MCP server, Mistral, or email API.

Each completed workflow records its trigger and completion metadata, aggregate
counts, and one email audit event per employee. Email events include recipient,
subject, full generated body, leave values, risk category, delivery status, and
provider message. The local database contains employee-related data; protect
it like other application data and do not commit the `data/` directory.

## Start the repository API

With the virtual environment activated, start the FastAPI service from the
repository root:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

You can verify that it is running by opening the interactive API docs at:

```text
http://127.0.0.1:8001/docs
```

The API provides these workflow endpoints:

- `GET /health` confirms that the repository API process is running.
- `POST /agent/trigger` runs the leave workflow.
- `GET /agent/pending-reviews` lists low-balance emails waiting for approval.
- `POST /agent/pending-reviews/{employee_id}` accepts a review action.
- `POST /leaves/send_email` is the local mock email endpoint used by the workflow.

The workflow audit API is available under `/workflows`. List endpoints return a
paginated object with `items`, `total`, `limit`, and `offset` fields.

- `POST /workflows/trigger` creates a workflow run by triggering the leave workflow.
- `GET /workflows` lists workflow runs. Optional query parameters are
  `status`, `workflow_type`, `limit`, and `offset`.
- `GET /workflows/{run_id}` returns one workflow run and its metadata.
- `DELETE /workflows/{run_id}` deletes a workflow run and its email audit events.
- `GET /workflows/{run_id}/emails` lists the employees and email outcomes for a
  run. Optional query parameters are `delivery_status`, `limit`, and `offset`.
- `GET /workflows/{run_id}/emails/{event_id}` returns one employee email event,
  including recipient, subject, body, leave values, risk category, and status.
- `PATCH /workflows/{run_id}/emails/{event_id}` updates an event's delivery
  status and provider message.
- `DELETE /workflows/{run_id}/emails/{event_id}` deletes one email audit event.

For example, list all email events for a workflow and filter to pending reviews:

```bash
curl http://127.0.0.1:8001/workflows/<workflow-run-id>/emails
curl 'http://127.0.0.1:8001/workflows/<workflow-run-id>/emails?delivery_status=pending_review'
```

Update an event after a human review:

```bash
curl -X PATCH http://127.0.0.1:8001/workflows/<workflow-run-id>/emails/<event-id> \
  -H 'Content-Type: application/json' \
  -d '{"delivery_status":"rejected","provider_message":"Rejected by HR reviewer"}'
```

## Run the leave agent

Keep the Frappe service, MCP server, and repository API running in separate
terminals. Then, from this repository root, run:

```bash
source .venv/bin/activate
sh scripts/run_agent.sh
```

The script starts `app/agentic_workflow/leave_agent.py`. It connects to the MCP
server, discovers the `hrms_find_employee` and `hrms_get_leave_balance` tools,
and triggers the leave email workflow.

You can run the same command without activating the virtual environment:

```bash
.venv/bin/python app/agentic_workflow/leave_agent.py
```

The workflow sends normal-risk emails immediately. When `HITL_ENABLED=true`,
low-balance or Loss-of-Pay-risk emails are stored as pending reviews instead of
being sent automatically.

## Trigger and review through the API

The agent can also be triggered through the FastAPI service:

```bash
curl -X POST http://127.0.0.1:8001/agent/trigger \
  -H 'Content-Type: application/json' \
  -d '{}'
```

List pending reviews:

```bash
curl http://127.0.0.1:8001/agent/pending-reviews
```

Approve or reject a pending review by replacing `<employee-id>` with the ID
returned by the previous request:

```bash
curl -X POST http://127.0.0.1:8001/agent/pending-reviews/<employee-id> \
  -H 'Content-Type: application/json' \
  -d '{"action":"approve"}'
```

To reject it, use `{"action":"reject"}` instead.

## Troubleshooting

- **Missing `MISTRAL_API_KEY`**: confirm that `.env` is in the repository root,
  next to `requirements.txt`.
- **MCP connection refused**: start the Frappe MCP server and confirm that
  `FRAPPE_MCP_URL` points to its `/mcp` endpoint.
- **Frappe authentication errors**: verify `FRAPPE_BASE_URL`,
  `FRAPPE_API_KEY`, and `FRAPPE_API_SECRET` in the MCP server's `.env`, then
  restart the MCP server.
- **Email request failures**: confirm that this repository's FastAPI service is
  running on port `8001` and that `EMAIL_API_BASE_URL` matches it.
- **No employees returned**: check the MCP server logs, the Frappe user's HRMS
  permissions, and `MCP_EMPLOYEE_QUERY`.

Never commit .env files or expose API keys in logs, screenshots, source code,
or documentation. If a real credential has been exposed, revoke or rotate it.