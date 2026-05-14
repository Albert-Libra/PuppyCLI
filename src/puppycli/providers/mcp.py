"""Generic MCP Streamable HTTP client — adapted from ScholarAIO.

Connects to local MCP servers for web search, content extraction, etc.
Configure via environment variables or .mcp.json.
"""
from __future__ import annotations

import json
from itertools import count
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MCP_PROTOCOL_VERSION = "2025-11-25"


class McpError(RuntimeError):
    """Base class for MCP client failures."""


class McpTransportError(McpError):
    """Raised when the MCP endpoint cannot be reached or decoded."""


class McpProtocolError(McpError):
    """Raised when a JSON-RPC or MCP protocol error is returned."""


class StreamableHttpMcpClient:
    """Minimal MCP Streamable HTTP client for tool calls."""

    def __init__(
        self,
        endpoint_url: str,
        *,
        api_key: str = "",
        client_name: str = "puppycli",
        client_version: str = "0.1.0",
        protocol_version: str = MCP_PROTOCOL_VERSION,
        timeout: int = 120,
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key = api_key.strip()
        self.client_name = client_name
        self.client_version = client_version
        self.protocol_version = protocol_version
        self.timeout = timeout
        self.session_id = ""
        self._initialized = False
        self._ids = count(1)

    def initialize(self) -> dict[str, Any]:
        """MCP lifecycle initialization."""
        if self._initialized:
            return {}

        result = self._request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version,
                },
            },
            ensure_initialized=False,
        )
        negotiated = result.get("protocolVersion")
        if isinstance(negotiated, str) and negotiated:
            self.protocol_version = negotiated

        self._request(
            "notifications/initialized",
            expect_response=False,
            ensure_initialized=False,
        )
        self._initialized = True
        return result

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a server tool."""
        return self._request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )

    def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        expect_response: bool = True,
        ensure_initialized: bool = True,
    ) -> dict[str, Any]:
        if ensure_initialized and not self._initialized:
            self.initialize()

        request_id: int | None = None
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if expect_response:
            request_id = next(self._ids)
            payload["id"] = request_id
        if params is not None:
            payload["params"] = params

        response = self._post(payload, expect_response=expect_response)
        if not expect_response:
            return {}

        error = response.get("error")
        if error:
            msg = str(error.get("message") if isinstance(error, dict) else error)
            raise McpProtocolError(msg)

        result = response.get("result")
        if isinstance(result, dict):
            return result
        return {}

    def _post(self, payload: dict[str, Any], *, expect_response: bool) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.protocol_version,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        req = Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                sid = _get_header(resp, "Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                raw = resp.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise McpTransportError(f"MCP HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise McpTransportError(f"Cannot connect to MCP endpoint: {exc.reason}") from exc

        if not raw.strip():
            return {}

        try:
            return json.loads(raw)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise McpTransportError(f"Cannot decode MCP response: {exc}") from exc


def call_mcp_tool(
    endpoint_url: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    api_key: str = "",
    timeout: int = 30,
) -> dict[str, Any]:
    """One-shot convenience wrapper for MCP tool call."""
    client = StreamableHttpMcpClient(endpoint_url, api_key=api_key, timeout=timeout)
    return client.call_tool(tool_name, arguments or {})


def _get_header(response: object, name: str) -> str | None:
    getter = getattr(response, "getheader", None)
    if callable(getter):
        value = getter(name)
        if value:
            return str(value)
    headers = getattr(response, "headers", None)
    if headers is not None:
        value = headers.get(name)
        if value:
            return str(value)
    return None
