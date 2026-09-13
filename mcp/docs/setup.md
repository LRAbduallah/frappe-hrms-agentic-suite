# Frappe HRMS MCP Setup Guide

This guide explains how to start the local Frappe HRMS services, configure the
MCP bridge, and connect an MCP-compatible AI client using either stdio or
Streamable HTTP.

> The canonical project documentation is now in [`../../docs/`](../../docs/).
> Use the repository-root `docker-compose.yml` and root `.env` for the complete
> stack. This file remains as an MCP-specific reference.

## Prerequisites

- Python 3.10 or newer
- Docker Desktop with Docker Compose
- An MCP-compatible client or agent
- A Frappe API key and API secret

Install the Python dependencies:

```bash
cd /absolute/path/to/frappe-hrms-agentic-suite/mcp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 1. Start Frappe HRMS with Docker

From the repository root, start the Docker services:

```bash
docker compose up -d --build
```

The compose file starts:

- MariaDB on the internal Docker network
- Redis on the internal Docker network
- Frappe Bench with HRMS installed by `docker/init.sh`

Frappe is exposed at:

```text
http://localhost:8000
```

The first startup downloads and installs Bench, ERPNext, and HRMS. It can take
several minutes. Follow the initialization logs with:

```bash
docker compose logs -f frappe
```

Verify that the site responds:

```bash
curl http://localhost:8000/api/method/frappe.ping
```

The initial Desk credentials are the values configured in the root `.env` file:

```text
Site: http://localhost:8000
user: Administrator 
password: value of FRAPPE_ADMIN_PASSWORD
```

Change the password before using this setup outside a local development
environment.

Stop the Docker services with:

```bash
docker compose down
```

The MariaDB data remains in the Docker volume unless the volume is explicitly
removed.

## 2. Create Frappe API Credentials

The MCP server authenticates to Frappe with token authentication:

```http
Authorization: token API_KEY:API_SECRET
```

Create an API user in Frappe Desk:

1. Open **User** in Frappe Desk.
2. Create or select a dedicated integration user.
3. Give it only the HRMS roles and DocType permissions needed by the agent.
4. Open **API Access** for that user.
5. Generate an API key and API secret.

Use a dedicated least-privilege user. Do not use the Administrator account for
normal agent access.

## 3. Configure the MCP Server

Create a `.env` file in the project root:n

```ini
FRAPPE_BASE_URL=http://localhost:8000
FRAPPE_API_KEY=replace_with_api_key
FRAPPE_API_SECRET=replace_with_api_secret
FRAPPE_MCP_MODE=production
FRAPPE_REQUEST_TIMEOUT=30
```

The values are loaded by `mcpp/config.py`.

### Modes

Use production mode for normal agents:

```ini
FRAPPE_MCP_MODE=production
```

Production mode exposes read, create, update, workflow, and HR helper tools. It
does not register document deletion or bulk creation.

Use admin mode only for controlled setup or migration work:

```ini
FRAPPE_MCP_MODE=admin
```

Admin mode additionally exposes document deletion and sequential bulk creation.
It does not bypass Frappe permissions.

Never commit `.env`. The repository `.gitignore` should keep credentials out of
source control.

## 4. Choose a Transport

Use **stdio** when the MCP client launches the server locally. This is the
recommended option for desktop clients because no network listener is required.

Use **Streamable HTTP** when the MCP server is a separate process or host and
the client connects to a URL. Put HTTP behind TLS, authentication, and network
restrictions before exposing it beyond a trusted local machine.

## 5. Stdio Setup

### Start the server manually

```bash
cd /absolute/path/to/frappe-mcp
.venv/bin/python run.py --mode production
```

The process waits for MCP protocol messages on stdin and writes responses to
stdout. Do not use this terminal for ordinary text while the server is running.

### Generic MCP client configuration

Most MCP clients use an `mcpServers` configuration map. Use an absolute path to
the virtual-environment Python executable and the absolute path to `run.py`:

```json
{
	"mcpServers": {
		"frappe-hr-production": {
			"command": "/absolute/path/to/frappe-mcp/.venv/bin/python",
			"args": [
				"/absolute/path/to/frappe-mcp/run.py",
				"--mode",
				"production"
			],
			"env": {
				"FRAPPE_BASE_URL": "http://localhost:8000",
				"FRAPPE_API_KEY": "replace_with_api_key",
				"FRAPPE_API_SECRET": "replace_with_api_secret",
				"FRAPPE_REQUEST_TIMEOUT": "30"
			}
		}
	}
}
```

The `env` block is optional when the MCP process can read the project `.env`.
Environment injection is useful when the client starts the process from an
unknown working directory.

For a temporary admin connection, use a separate server entry:

```json
{
	"mcpServers": {
		"frappe-hr-admin": {
			"command": "/absolute/path/to/frappe-mcp/.venv/bin/python",
			"args": [
				"/absolute/path/to/frappe-mcp/run.py",
				"--mode",
				"admin"
			],
			"env": {
				"FRAPPE_BASE_URL": "http://localhost:8000",
				"FRAPPE_API_KEY": "replace_with_admin_api_key",
				"FRAPPE_API_SECRET": "replace_with_admin_api_secret"
			}
		}
	}
}
```

Keep production and admin entries separate so an agent does not receive
destructive tools during ordinary work.

## 6. Streamable HTTP Setup

### Start the HTTP server

```bash
cd /absolute/path/to/frappe-mcp
.venv/bin/python run.py --http --mode production --port 8800
```

The MCP endpoint is served from the local process on port `8800`.

The port can be changed when another process already uses it:

```bash
.venv/bin/python run.py --http --mode production --port 8801
```

### Generic HTTP client configuration

For clients that support a remote MCP server URL, configure:

```json
{
	"mcpServers": {
		"frappe-hr-production-http": {
			"url": "http://localhost:8800/mcp"
		}
	}
}
```

The exact URL setting name varies by MCP client. Some clients call it `url`,
`serverUrl`, or `endpoint`. Use the client's Streamable HTTP configuration
field and point it to the server endpoint exposed by the MCP library.

The Frappe API credentials remain on the MCP server host. They should not be
placed in the remote MCP client's configuration.

### HTTP deployment checklist

Before exposing the service outside a trusted local network:

- Terminate TLS at the server or a reverse proxy.
- Add MCP-client authentication at the proxy or service boundary.
- Restrict access by network or VPN where possible.
- Keep Frappe API credentials in environment variables or a secret manager.
- Use production mode unless destructive setup tools are explicitly required.
- Set a finite `FRAPPE_REQUEST_TIMEOUT`.

## 7. Recommended Agent Setup Sequence

An agent should discover the Frappe structure before writing data:

1. Call `hrms_list_doctypes` if the exact DocType name is uncertain.
2. Call `frappe_get_doctype_schema` before creating or updating a document.
3. Call `frappe_get_link_options` for linked values such as Department,
   Company, Designation, or Leave Type.
4. Call the create or update tool.
5. Call `frappe_submit_document` separately for a submittable document when
   the business process requires submission.
6. Call `frappe_get_document` or `frappe_get_document_history` to confirm the
   result when needed.

Example leave flow:

```text
hrms_find_employee
				-> frappe_get_link_options (Leave Type)
				-> hrms_apply_leave
				-> frappe_submit_document (when required)
				-> frappe_get_document
```

`hrms_apply_leave` creates the Leave Application. It does not submit it by
itself, so submission must be a deliberate separate step.

## 8. Smoke Test

After connecting an MCP client, run these read-only checks:

```text
1. Call hrms_list_doctypes.
2. Call frappe_get_doctype_schema for Employee.
3. Call frappe_get_link_options for Department.
4. Call frappe_list_documents for Employee with limit 1.
```

Expected results:

- The DocType registry is returned.
- Employee field metadata is returned.
- Existing Department names are returned, or an empty list if none exist.
- Frappe returns zero or one Employee document without an authentication or
  permission error.

## 9. Troubleshooting

### `Missing FRAPPE_API_KEY or FRAPPE_API_SECRET`

Check `.env`, the MCP client's `env` block, and the process working directory.

### `Could not connect to Frappe`

Check Docker and confirm that Frappe responds on port 8000:

```bash
docker compose ps
curl http://localhost:8000/api/method/frappe.ping
```

### `Permission denied`

Add the required DocType or action permissions to the dedicated Frappe API
user. Admin MCP mode does not override Frappe permissions.

### `ModuleNotFoundError: No module named 'mcp'`

Install the project dependencies inside the virtual environment:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

### MCP client cannot start stdio server

Use absolute paths for both the Python executable and `run.py`. Also check that
the `.venv` exists and that the MCP client is not launching the command from a
different operating system environment.

### HTTP client cannot connect

Confirm that the MCP process is running and that the configured port matches
the `--port` argument. If the port is occupied, choose another port.

## 10. Shutdown

Stop the MCP server with `Ctrl+C`.

Stop Frappe and its supporting containers with:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the
local MariaDB volume and all local Frappe data.
