"""Logging configuration shared by MCP and data population entrypoints."""

from __future__ import annotations

import logging
import os
import sys


LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s "
    "[%(filename)s:%(lineno)d] %(message)s"
)


def configure_logging() -> None:
    """Configure diagnostic logs without writing to stdout."""
    logging.basicConfig(
        level=os.environ.get("FRAPPE_LOG_LEVEL", "INFO").upper(),
        format=LOG_FORMAT,
        stream=sys.stderr,
    )