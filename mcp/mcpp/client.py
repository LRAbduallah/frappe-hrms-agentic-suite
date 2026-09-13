"""Production-ready asynchronous client for Frappe REST API & RPC methods."""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from mcpp.config import (
    FRAPPE_API_KEY,
    FRAPPE_API_SECRET,
    FRAPPE_BASE_URL,
    FRAPPE_REQUEST_TIMEOUT,
    FRAPPE_SCHEMA_CACHE_TTL,
)


logger = logging.getLogger(__name__)
_LOG_VALUE_LIMIT = 1_500
_SENSITIVE_LOG_KEYS = {"authorization", "api_key", "api_secret", "password", "secret", "token"}


class FrappeAPIError(Exception):
    """Raised for any failed Frappe API call with an LLM-safe message."""

    def __init__(self, status_code: int, message: str, raw: Any = None):
        self.status_code = status_code
        self.message = message
        self.raw = raw
        super().__init__(f"[{status_code}] {message}")


def _url_quote(value: str) -> str:
    return quote(str(value), safe="")


def _extract_error_message(status_code: int, body: Any) -> str:
    if isinstance(body, dict):
        if body.get("exception"):
            return str(body["exception"])
        if body.get("_server_messages"):
            try:
                # _server_messages is often a JSON string array of JSON strings
                msgs = json.loads(body["_server_messages"])
                parsed = [json.loads(m).get("message") for m in msgs if isinstance(m, str)]
                return " | ".join(filter(None, parsed))
            except Exception:
                return str(body["_server_messages"])
        if body.get("message"):
            return str(body["message"])

    if status_code == 401:
        return "Unauthorized: Check FRAPPE_API_KEY and FRAPPE_API_SECRET."
    if status_code == 403:
        return "Permission denied. The API user lacks access to this DocType, document, or action."
    if status_code == 404:
        return "Not found. Verify the DocType name and document name are correct."
    if status_code == 409:
        return "Conflict: Document modified by another user or duplicate entry."
    if status_code == 417:
        return "Validation error. Check required fields, child tables, and values."
    return f"Request failed with HTTP {status_code}."


def _redact_for_log(value: Any) -> Any:
    """Remove credential-like fields before request or response data is logged."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in _SENSITIVE_LOG_KEYS else _redact_for_log(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_for_log(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_for_log(item) for item in value)
    return value


def _log_value(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            pass
    rendered = json.dumps(_redact_for_log(value), default=str, separators=(",", ":"))
    if len(rendered) > _LOG_VALUE_LIMIT:
        return f"{rendered[:_LOG_VALUE_LIMIT]}... [truncated]"
    return rendered


class FrappeClient:
    """Async Frappe REST API and RPC Client."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or FRAPPE_BASE_URL).rstrip("/")
        self.api_key = api_key or FRAPPE_API_KEY
        self.api_secret = api_secret or FRAPPE_API_SECRET
        self.timeout = timeout or FRAPPE_REQUEST_TIMEOUT
        self._meta_cache: dict[str, tuple[float, dict]] = {}
        self._meta_ttl = FRAPPE_SCHEMA_CACHE_TTL

    def _auth_header(self) -> dict[str, str]:
        if not self.api_key or not self.api_secret:
            raise FrappeAPIError(
                401,
                "Missing FRAPPE_API_KEY or FRAPPE_API_SECRET. "
                "Ensure they are set in .env or environment variables.",
            )
        return {"Authorization": f"token {self.api_key}:{self.api_secret}"}

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        headers = {**self._auth_header(), "Accept": "application/json"}
        started_at = time.perf_counter()

        logger.info(
            "Frappe API request: method=%s url=%s params=%s json=%s",
            method,
            url,
            _log_value(params),
            _log_value(json_body),
        )

        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            try:
                resp = await http_client.request(
                    method, url, params=params, json=json_body, headers=headers
                )
            except httpx.TimeoutException as e:
                logger.exception(
                    "Frappe API timeout: method=%s url=%s elapsed_ms=%.1f",
                    method,
                    url,
                    (time.perf_counter() - started_at) * 1000,
                )
                raise FrappeAPIError(504, f"Request to Frappe timed out: {e}") from e
            except httpx.ConnectError as e:
                logger.exception(
                    "Frappe API connection error: method=%s url=%s elapsed_ms=%.1f",
                    method,
                    url,
                    (time.perf_counter() - started_at) * 1000,
                )
                raise FrappeAPIError(
                    502,
                    f"Could not connect to Frappe at {self.base_url}. "
                    f"Verify site URL and ensure Frappe is running. ({e})",
                ) from e

        logger.info(
            "Frappe API response: method=%s url=%s status=%s elapsed_ms=%.1f body=%s",
            method,
            url,
            resp.status_code,
            (time.perf_counter() - started_at) * 1000,
            _log_value(resp.text),
        )

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise FrappeAPIError(resp.status_code, _extract_error_message(resp.status_code, body), body)

        if not resp.content:
            return None
        return resp.json()

    # --- Document Resource Operations (/api/resource/<DocType>) ---

    async def get_list(
        self,
        doctype: str,
        fields: list[str] | None = None,
        filters: list | dict | None = None,
        order_by: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        params: dict[str, Any] = {"limit_page_length": limit, "limit_start": offset}
        if fields:
            params["fields"] = json.dumps(fields)
        if filters:
            params["filters"] = json.dumps(filters)
        if order_by:
            params["order_by"] = order_by

        result = await self.request("GET", f"/api/resource/{_url_quote(doctype)}", params=params)
        return result.get("data", []) if isinstance(result, dict) else []

    async def get_doc(self, doctype: str, name: str) -> dict:
        result = await self.request("GET", f"/api/resource/{_url_quote(doctype)}/{_url_quote(name)}")
        return result.get("data", {}) if isinstance(result, dict) else {}

    async def create_doc(self, doctype: str, fields: dict[str, Any]) -> dict:
        payload = {"doctype": doctype, **fields}
        result = await self.request("POST", f"/api/resource/{_url_quote(doctype)}", json_body=payload)
        return result.get("data", {}) if isinstance(result, dict) else {}

    async def update_doc(self, doctype: str, name: str, fields: dict[str, Any]) -> dict:
        result = await self.request(
            "PUT", f"/api/resource/{_url_quote(doctype)}/{_url_quote(name)}", json_body=fields
        )
        return result.get("data", {}) if isinstance(result, dict) else {}

    async def delete_doc(self, doctype: str, name: str) -> bool:
        await self.request("DELETE", f"/api/resource/{_url_quote(doctype)}/{_url_quote(name)}")
        return True

    # --- Schema & Metadata Operations ---

    async def get_doctype_meta(self, doctype: str) -> dict:
        """Fetch DocType metadata: fields, child tables, options, permissions."""
        cached = self._meta_cache.get(doctype)
        now = time.time()
        if cached and now - cached[0] < self._meta_ttl:
            return cached[1]

        meta: dict = {}
        # frappe.desk.form.load.getdoctype is whitelisted and universally accessible
        try:
            result = await self.call_method(
                "frappe.desk.form.load.getdoctype",
                params={"doctype": doctype},
            )
            if isinstance(result, dict) and result.get("docs"):
                meta = result["docs"][0]
        except Exception:
            meta = {}

        if not meta:
            result = await self.request(
                "GET",
                f"/api/resource/DocType/{_url_quote(doctype)}",
            )
            meta = result.get("data", {}) if isinstance(result, dict) else {}

        if meta:
            self._meta_cache[doctype] = (now, meta)
        return meta

    async def get_count(self, doctype: str, filters: list | dict | None = None) -> int:
        params: dict[str, Any] = {"doctype": doctype}
        if filters:
            params["filters"] = json.dumps(filters)
        result = await self.request("GET", "/api/method/frappe.client.get_count", params=params)
        return int(result.get("message", 0)) if isinstance(result, dict) else int(result or 0)

    # --- RPC Whitelist Methods (/api/method/<endpoint>) ---

    async def call_method(
        self, method: str, params: dict[str, Any] | None = None, post: bool = False
    ) -> Any:
        http_verb = "POST" if post else "GET"
        if post:
            result = await self.request(http_verb, f"/api/method/{method}", json_body=params)
        else:
            result = await self.request(http_verb, f"/api/method/{method}", params=params)
        return result.get("message") if isinstance(result, dict) and "message" in result else result
