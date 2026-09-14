from strands.hooks.events import AfterToolCallEvent, AfterToolsEvent, BeforeToolCallEvent

from app.agentic_workflow.hooks.workflow_hooks import WorkflowHookProvider
from app.agentic_workflow.leave_agent import _terminal_workflow_failure
from app.agentic_workflow.services.mcp_service import _items, get_employee_leave_balances


def _provider() -> WorkflowHookProvider:
    return object.__new__(WorkflowHookProvider)


def _tool_use() -> dict[str, object]:
    return {
        "name": "run_leave_email_workflow",
        "toolUseId": "workflow-test",
        "input": {},
    }


def test_workflow_exception_ends_tool_batch_without_retry() -> None:
    invocation_state: dict[str, object] = {}
    event = AfterToolCallEvent(
        agent=object(),
        selected_tool=None,
        tool_use=_tool_use(),
        invocation_state=invocation_state,
        result={"status": "error", "content": []},
        exception=RuntimeError("MCP unavailable"),
    )
    provider = _provider()

    provider.on_after_tool_call(event)
    after_tools = AfterToolsEvent(
        agent=object(),
        message={"role": "user", "content": []},
        invocation_state=invocation_state,
    )
    provider.on_after_tools(after_tools)

    assert event.retry is False
    assert after_tools.end_turn == "Leave workflow failed: MCP unavailable"
    assert invocation_state[provider._TERMINAL_FAILURE_KEY] == after_tools.end_turn
    assert _terminal_workflow_failure(type("Response", (), {"state": invocation_state})()) == after_tools.end_turn


def test_workflow_error_result_ends_tool_batch() -> None:
    invocation_state: dict[str, object] = {}
    event = AfterToolCallEvent(
        agent=object(),
        selected_tool=None,
        tool_use=_tool_use(),
        invocation_state=invocation_state,
        result={"status": "error", "content": [{"text": "tool failed"}]},
    )
    provider = _provider()

    provider.on_after_tool_call(event)
    after_tools = AfterToolsEvent(
        agent=object(),
        message={"role": "user", "content": []},
        invocation_state=invocation_state,
    )
    provider.on_after_tools(after_tools)

    assert after_tools.end_turn == "Leave workflow failed."


def test_workflow_cooldown_cancellation_is_terminal(monkeypatch) -> None:
    invocation_state: dict[str, object] = {}
    provider = _provider()
    monkeypatch.setattr(provider, "_workflow_allowed", lambda: False)
    event = BeforeToolCallEvent(
        agent=object(),
        selected_tool=None,
        tool_use=_tool_use(),
        invocation_state=invocation_state,
    )

    provider.on_before_tool_call(event)
    after_tools = AfterToolsEvent(
        agent=object(),
        message={"role": "user", "content": []},
        invocation_state=invocation_state,
    )
    provider.on_after_tools(after_tools)

    assert event.cancel_tool
    assert after_tools.end_turn == event.cancel_tool


def test_mcp_items_accepts_json_text_and_common_wrappers() -> None:
    employee = {"employee": "HR-EMP-00001", "employee_name": "Jane Doe"}

    assert _items('[{"employee": "HR-EMP-00001", "employee_name": "Jane Doe"}]', "employees") == [employee]
    assert _items({"data": {"employees": [employee]}}, "employees") == [employee]
    assert _items({"result": '[{"employee": "HR-EMP-00001", "employee_name": "Jane Doe"}]'}, "employees") == [employee]


def test_mcp_items_surfaces_server_error_payload() -> None:
    try:
        _items({"error": "Could not connect to Frappe", "status_code": 502}, "employees")
    except ValueError as exc:
        assert str(exc) == "MCP tool failed (status 502): Could not connect to Frappe"
    else:
        raise AssertionError("Expected MCP server error payload to raise ValueError")


def test_mcp_tool_arguments_are_nested_under_params(monkeypatch) -> None:
    calls = []

    class FakeClient:
        def call_tool_sync(self, **kwargs):
            calls.append(kwargs)
            if kwargs["name"] == "hrms_find_employee":
                return {
                    "content": [
                        {
                            "text": '[{"employee": "HR-EMP-00001", "employee_name": "Jane Doe", "company_email": "jane@example.com"}]'
                        }
                    ]
                }
            return {
                "content": [
                    {
                        "text": '{"employee": "HR-EMP-00001", "balances": [{"allocated": 20, "balance": 15}]}'
                    }
                ]
            }

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        "app.agentic_workflow.services.mcp_service.mcp_client",
        lambda _settings: FakeClient(),
    )

    class Settings:
        MCP_EMPLOYEE_QUERY = "*"

    employees = get_employee_leave_balances(Settings())

    assert len(employees) == 1
    assert employees[0].total_leave_balance_allocated == 20
    assert employees[0].leave_balance_used_this_month == 5
    assert employees[0].leave_balance_remaining == 15
    assert all(call["arguments"].keys() == {"params"} for call in calls)
    assert calls[0]["arguments"]["params"]["query"] == ""