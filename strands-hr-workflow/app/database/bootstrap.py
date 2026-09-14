import os
import re
from typing import Any

import pymysql

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


def _identifier(name: str, setting_name: str) -> str:
    if not _IDENTIFIER_PATTERN.fullmatch(name):
        raise ValueError(f"{setting_name} must contain only letters, numbers, and underscores")
    return f"`{name}`"


def _connect(**kwargs: Any) -> Any:
    return pymysql.connect(**kwargs)


def bootstrap_database() -> None:
    host = os.getenv("MARIADB_HOST", "mariadb").strip()
    port = int(os.getenv("MARIADB_PORT", "3306"))
    root_password = _required_setting("MARIADB_ROOT_PASSWORD")
    database = _required_setting("STRANDS_DB_NAME")
    username = _required_setting("STRANDS_DB_USER")
    password = _required_setting("STRANDS_DB_PASSWORD")

    database_identifier = _identifier(database, "STRANDS_DB_NAME")
    user_identifier = _identifier(username, "STRANDS_DB_USER")

    connection = _connect(
        host=host,
        port=port,
        user="root",
        password=root_password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {database_identifier} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute(
                f"CREATE USER IF NOT EXISTS {user_identifier}@'%%' IDENTIFIED BY %s",
                (password,),
            )
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON {database_identifier}.* "
                f"TO {user_identifier}@'%%' IDENTIFIED BY %s",
                (password,),
            )
            cursor.execute("FLUSH PRIVILEGES")
    finally:
        connection.close()


if __name__ == "__main__":
    bootstrap_database()
    print("Strands workflow database is ready")
