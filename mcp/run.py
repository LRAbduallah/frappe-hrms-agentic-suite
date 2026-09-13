#!/usr/bin/env python3
"""Entrypoint for Frappe HR MCP Server.

Usage:
    # Run in default production mode (Read, Create, Update, Submit - NO Delete):
    python run.py

    # Run in admin / setup mode (Full CRUD + Delete + Bulk Seeding):
    python run.py --mode admin

    # Run as HTTP streamable service:
    python run.py --http --port 8800
    python run.py --http --mode admin --port 8801
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure root package directory is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from mcpp.server import build_server
from mcpp.logging import configure_logging


logger = logging.getLogger(__name__)


def main():
    configure_logging()

    parser = argparse.ArgumentParser(description="Frappe HRMS Model Context Protocol (MCP) Server")
    parser.add_argument(
        "--mode",
        choices=["production", "admin"],
        default=None,
        help="Operational mode: 'production' (safe agent mode, no delete) or 'admin' (full CRUD + delete)",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run using streamable HTTP transport instead of default stdio",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8800,
        help="Port to bind when running with --http (default: 8800)",
    )

    args = parser.parse_args()
    logger.info(
        "Starting Frappe HR MCP: mode=%s transport=%s port=%s log_level=%s",
        args.mode or "configured default",
        "streamable-http" if args.http else "stdio",
        args.port if args.http else "n/a",
        logging.getLevelName(logging.getLogger().getEffectiveLevel()),
    )
    mcp_app = build_server(mode=args.mode)

    if args.http:
        logger.info("Starting streamable HTTP transport on port %s", args.port)
        mcp_app.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=args.port,
        )
    else:
        logger.info("Starting stdio transport")
        mcp_app.run()


if __name__ == "__main__":
    main()
