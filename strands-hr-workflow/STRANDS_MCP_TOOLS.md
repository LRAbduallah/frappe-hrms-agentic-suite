# Frappe MCP Tools for Strands

This document describes how to connect a Strands application to the Frappe HRMS MCP server and the tools exposed by the server.

## MCP Endpoint

Start the MCP server from the repository root:

```bash
.venv/bin/python run.py --http --mode production --port 8800
```

The Streamable HTTP endpoint is:

```text
http://localhost:8800/mcp
```

The Frappe API remains on:

```text
http://localhost:8000
```

## Connect from Strands

Strands can discover the MCP tools automatically. The tools do not need to be manually recreated as native Strands tools.

```python
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamable_http_client


mcp_client = MCPClient(
    lambda: streamable_http_client("http://localhost:8800/mcp")
)

with mcp_client:
    tools = mcp_client.list_tools_sync()

    agent = Agent(
        tools=tools,
        system_prompt="""
You are an HRMS assistant connected to Frappe through MCP.

Before creating or updating a document:
1. Confirm the exact DocType.
2. Call frappe_get_doctype_schema.
3. Call frappe_get_link_options for Link fields.
4. Confirm the user's intended mutation before executing it.

Use hrms_find_employee before employee-specific actions.
Use hrms_get_leave_balance before applying leave.
Do not submit or cancel documents unless explicitly requested.
Never use destructive administrative tools unless explicitly authorized.
""",
    )

    response = agent("Find active employees matching Jane.")
    print(response)
```

The exact `MCPClient` import or method name can vary by Strands SDK version. The important parts are the Streamable HTTP transport and the endpoint URL.

## Production Tools

The production server exposes 16 tools. Production mode allows reads, creates, updates, and workflow actions, but does not expose document deletion or bulk creation.

### `hrms_list_doctypes`

Lists the curated HRMS DocTypes supported by the server.

Input schema:

```json
{
  "type": "object",
  "properties": {
    "category": {
      "type": ["string", "null"],
      "description": "Optional category filter, such as Core HR, Attendance, Leave, Payroll, or Recruitment."
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{}
```

Read-only. Use this when the exact Frappe DocType name is uncertain.

### `frappe_get_doctype_schema`

Returns fields, field types, required fields, defaults, link options, and submission status for a DocType.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype"],
  "properties": {
    "doctype": {
      "type": "string",
      "description": "Exact Frappe DocType name."
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Employee"
}
```

Read-only. Call this before creating or updating documents.

### `frappe_get_link_options`

Returns valid existing names for a Link field.

Input schema:

```json
{
  "type": "object",
  "required": ["target_doctype"],
  "properties": {
    "target_doctype": {
      "type": "string",
      "description": "Target DocType, such as Department, Leave Type, Company, or Branch."
    },
    "search": {
      "type": ["string", "null"],
      "description": "Optional substring filter."
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 25
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "target_doctype": "Department",
  "search": "Engineering",
  "limit": 10
}
```

Read-only.

### `frappe_list_documents`

Lists documents of any Frappe DocType with optional fields, filters, sorting, and pagination.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype"],
  "properties": {
    "doctype": {
      "type": "string",
      "description": "Frappe DocType name."
    },
    "fields": {
      "type": ["array", "null"],
      "items": {"type": "string"},
      "description": "Fields to return."
    },
    "filters": {
      "type": ["array", "object", "null"],
      "description": "Frappe filters, for example [[\"status\", \"=\", \"Active\"]]."
    },
    "order_by": {
      "type": ["string", "null"],
      "description": "Sort order, such as creation desc."
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 200,
      "default": 20
    },
    "offset": {
      "type": "integer",
      "minimum": 0,
      "default": 0
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Employee",
  "fields": ["name", "employee_name", "company_email", "department", "status"],
  "filters": [["status", "=", "Active"]],
  "order_by": "employee_name asc",
  "limit": 20,
  "offset": 0
}
```

Read-only.

### `frappe_get_document`

Fetches one complete document, including child tables.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "name"],
  "properties": {
    "doctype": {"type": "string"},
    "name": {"type": "string", "description": "Document name or primary key."}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Employee",
  "name": "HR-EMP-00001"
}
```

Read-only.

### `frappe_create_document`

Creates a document of any DocType and returns the created record.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "fields"],
  "properties": {
    "doctype": {"type": "string"},
    "fields": {
      "type": "object",
      "additionalProperties": true,
      "description": "Field values for the new document."
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Department",
  "fields": {
    "department_name": "Engineering",
    "company": "My Company"
  }
}
```

Creates data. Call `frappe_get_doctype_schema` first.

### `frappe_update_document`

Updates fields on an existing document.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "name", "fields"],
  "properties": {
    "doctype": {"type": "string"},
    "name": {"type": "string"},
    "fields": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Employee",
  "name": "HR-EMP-00001",
  "fields": {
    "company_email": "jane@example.com"
  }
}
```

Modifies data.

### `frappe_submit_document`

Submits a draft document by setting `docstatus` to `1`.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "name"],
  "properties": {
    "doctype": {"type": "string"},
    "name": {"type": "string"}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Leave Application",
  "name": "HR-LAP-00001"
}
```

Changes workflow state. Use only for submittable documents.

### `frappe_cancel_document`

Cancels a submitted document by setting `docstatus` to `2`.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "name"],
  "properties": {
    "doctype": {"type": "string"},
    "name": {"type": "string"}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Leave Application",
  "name": "HR-LAP-00001"
}
```

Changes workflow state.

### `frappe_get_document_history`

Returns timeline comments and communications associated with a document.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "name"],
  "properties": {
    "doctype": {"type": "string"},
    "name": {"type": "string"}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Employee",
  "name": "HR-EMP-00001"
}
```

Read-only.

### `hrms_get_leave_balance`

Returns allocated and remaining leave balances for an employee.

Input schema:

```json
{
  "type": "object",
  "required": ["employee"],
  "properties": {
    "employee": {"type": "string", "description": "Employee ID."},
    "date": {
      "type": ["string", "null"],
      "description": "Balance date in YYYY-MM-DD format."
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "employee": "HR-EMP-00001",
  "date": "2026-09-08"
}
```

Read-only.

### `hrms_apply_leave`

Creates a Leave Application with status `Open`.

Input schema:

```json
{
  "type": "object",
  "required": ["employee", "leave_type", "from_date", "to_date"],
  "properties": {
    "employee": {"type": "string"},
    "leave_type": {"type": "string"},
    "from_date": {"type": "string", "description": "YYYY-MM-DD"},
    "to_date": {"type": "string", "description": "YYYY-MM-DD"},
    "reason": {"type": ["string", "null"]},
    "half_day": {"type": "boolean", "default": false},
    "half_day_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "employee": "HR-EMP-00001",
  "leave_type": "Casual Leave",
  "from_date": "2026-09-15",
  "to_date": "2026-09-16",
  "reason": "Personal appointment",
  "half_day": false
}
```

Creates data but does not submit the application. Call `frappe_submit_document` separately if submission is required.

### `hrms_get_attendance`

Returns attendance records for an employee and date range.

Input schema:

```json
{
  "type": "object",
  "required": ["employee", "from_date", "to_date"],
  "properties": {
    "employee": {"type": "string"},
    "from_date": {"type": "string", "description": "YYYY-MM-DD"},
    "to_date": {"type": "string", "description": "YYYY-MM-DD"}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "employee": "HR-EMP-00001",
  "from_date": "2026-09-01",
  "to_date": "2026-09-08"
}
```

Read-only.

### `hrms_mark_attendance`

Creates an Attendance record.

Input schema:

```json
{
  "type": "object",
  "required": ["employee", "attendance_date", "status"],
  "properties": {
    "employee": {"type": "string"},
    "attendance_date": {"type": "string", "description": "YYYY-MM-DD"},
    "status": {
      "type": "string",
      "enum": ["Present", "Absent", "Half Day", "On Leave"]
    },
    "working_hours": {"type": ["number", "null"]}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "employee": "HR-EMP-00001",
  "attendance_date": "2026-09-08",
  "status": "Present",
  "working_hours": 8
}
```

Creates data. This operation is not idempotent, so avoid blindly retrying it.

### `hrms_get_salary_slips`

Returns salary slips with gross pay, deductions, and net pay.

Input schema:

```json
{
  "type": "object",
  "properties": {
    "employee": {"type": ["string", "null"]},
    "start_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
    "end_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 12}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "employee": "HR-EMP-00001",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "limit": 12
}
```

Read-only.

### `hrms_find_employee`

Searches employees by name, employee ID, or company email. The implementation searches employee name first, then ID, then company email.

Input schema:

```json
{
  "type": "object",
  "required": ["query"],
  "properties": {
    "query": {
      "type": "string",
      "description": "Employee name, ID, email, or department."
    },
    "status": {
      "type": ["string", "null"],
      "default": "Active",
      "description": "Employee status. Use null to search all statuses."
    },
    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 15}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "query": "Jane",
  "status": "Active",
  "limit": 10
}
```

Read-only.

## Admin-only Tools

These tools are not available in production mode. Start the server in admin mode to expose them:

```bash
.venv/bin/python run.py --http --mode admin --port 8800
```

### `frappe_delete_document`

Permanently deletes a document.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "name"],
  "properties": {
    "doctype": {"type": "string"},
    "name": {"type": "string"}
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Employee",
  "name": "HR-EMP-00001"
}
```

Destructive. Use only for controlled administrative operations.

### `frappe_bulk_create_documents`

Creates multiple documents sequentially. The operation is not transactional: earlier records may be created even when later records fail.

Input schema:

```json
{
  "type": "object",
  "required": ["doctype", "documents"],
  "properties": {
    "doctype": {"type": "string"},
    "documents": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": false
}
```

Example:

```json
{
  "doctype": "Department",
  "documents": [
    {
      "department_name": "Engineering",
      "company": "My Company"
    },
    {
      "department_name": "Human Resources",
      "company": "My Company"
    }
  ]
}
```

## Recommended Tool Order

For read operations:

1. Use `hrms_find_employee` or `frappe_list_documents` to find records.
2. Use `frappe_get_document` to retrieve a complete record.
3. Use `frappe_get_document_history` when timeline information is needed.

For creating or updating documents:

1. Use `hrms_list_doctypes` when the DocType is uncertain.
2. Use `frappe_get_doctype_schema` to identify required fields.
3. Use `frappe_get_link_options` to validate Link values.
4. Ask the user for confirmation before writing data.
5. Call the create or update tool.
6. Call `frappe_submit_document` separately when the workflow requires submission.

For leave:

1. Call `hrms_find_employee`.
2. Call `hrms_get_leave_balance`.
3. Confirm the leave type and date range.
4. Call `hrms_apply_leave`.
5. Submit the created application separately only when explicitly requested.

## Read-only Test Prompts

```text
List the available HRMS DocTypes.
```

```text
Find active employees matching Jane.
```

```text
Show the Employee DocType schema.
```

```text
Find the leave balance for employee HR-EMP-00001.
```

```text
Show attendance for HR-EMP-00001 from 2026-09-01 to 2026-09-08.
```

## Configuration and Security

The MCP server reads Frappe credentials from the server environment or `.env` file:

```ini
FRAPPE_BASE_URL=http://localhost:8000
FRAPPE_API_KEY=your_api_key
FRAPPE_API_SECRET=your_api_secret
FRAPPE_MCP_MODE=production
FRAPPE_REQUEST_TIMEOUT=30
```

Do not put Frappe API credentials in the Strands client. They remain on the MCP server host.

Before exposing the MCP endpoint outside the local machine, add TLS, authentication, and network restrictions.
