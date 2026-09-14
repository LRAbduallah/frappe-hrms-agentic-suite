from types import SimpleNamespace

import pytest

from app.database import bootstrap


def test_identifier_allows_database_names() -> None:
    assert bootstrap._identifier("strands_workflow", "STRANDS_DB_NAME") == "`strands_workflow`"


def test_identifier_rejects_sql_fragments() -> None:
    with pytest.raises(ValueError, match="STRANDS_DB_NAME"):
        bootstrap._identifier("workflow; DROP DATABASE frappe", "STRANDS_DB_NAME")


def test_bootstrap_creates_database_and_grants_dedicated_user(monkeypatch) -> None:
    statements: list[tuple[str, object]] = []

    class FakeCursor:
        def execute(self, statement: str, parameters: object = None) -> None:
            statements.append((statement, parameters))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            return None

    captured: dict[str, object] = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return FakeConnection()

    monkeypatch.setattr(bootstrap, "_connect", fake_connect)
    monkeypatch.setenv("MARIADB_ROOT_PASSWORD", "root-password")
    monkeypatch.setenv("STRANDS_DB_NAME", "strands_workflow")
    monkeypatch.setenv("STRANDS_DB_USER", "strands_workflow")
    monkeypatch.setenv("STRANDS_DB_PASSWORD", "workflow-password")

    bootstrap.bootstrap_database()

    assert captured["host"] == "mariadb"
    assert any("CREATE DATABASE IF NOT EXISTS `strands_workflow`" in statement for statement, _ in statements)
    assert any("CREATE USER IF NOT EXISTS `strands_workflow`@'%'" in statement for statement, _ in statements)
    assert any("GRANT ALL PRIVILEGES ON `strands_workflow`.*" in statement for statement, _ in statements)
    assert ("root-password" not in [parameter for _, parameter in statements])
    assert ("workflow-password",) in [parameter for _, parameter in statements]
