"""Stdio MCP client harness for slice 05. Speaks real JSON-RPC, not library calls."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, InitializeResult

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = Path(__file__).resolve().parent

REQUIRED_TOOLS = (
    "lookup_company",
    "google_overview",
    "google_news",
    "google_profile",
    "google_earnings",
    "google_financials",
    "google_coverage",
    "list_official_reports",
    "download_official_report",
    "read_official_report",
    "search_official_report",
)

FORBIDDEN_TOOL_NAMES = (
    "google_finance_call_rpc",
    "google_finance_call_dataset",
    "google_finance_call_quote_dataset",
    "google_finance_batch_call",
    "google_finance_get_quote_holdings",
)

INSTRUCTION_PHRASES = (
    "Google Finance is primary for everyday company questions and structured tables",
    "Saudi Exchange PDFs are for official reports, notes, and original evidence",
    "does not itself perform research",
    "unknown quote freshness is not real-time",
    "Google tables are not audited filings",
    "PDF page citations apply only to PDF-derived facts",
)


def server_env(
    storage: Path,
    *,
    hook: str | None = "mcp_hooks:install_full",
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env: dict[str, str] = {
        "PYTHONPATH": os.pathsep.join((str(ROOT), str(SRC), str(TESTS))),
        "PYTHONUNBUFFERED": "1",
        "SAUDI_REPORTS_STORAGE": str(storage),
        "SAUDI_MCP_MIN_INTERVAL": "0",
    }
    if hook:
        env["SAUDI_MCP_HOOK"] = hook
    if extra:
        env.update(extra)
    return env


def server_params(
    storage: Path,
    *,
    hook: str | None = "mcp_hooks:install_full",
    extra: Mapping[str, str] | None = None,
    live: bool = False,
) -> StdioServerParameters:
    env = server_env(storage, hook=None if live else hook, extra=extra)
    if live:
        env["SAUDI_LIVE_GOOGLE"] = os.environ.get("SAUDI_LIVE_GOOGLE", "1")
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "saudi_exchange_reports.mcp"],
        env=env,
        cwd=str(ROOT),
    )


def parse_tool(result: CallToolResult) -> dict[str, Any]:
    if result.structuredContent:
        return dict(result.structuredContent)
    if not result.content:
        return {}
    block = result.content[0]
    text = getattr(block, "text", None)
    if not text:
        return {}
    return json.loads(text)


async def with_session(
    params: StdioServerParameters,
    body: Callable,
) -> Any:
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            return await body(session, init)


def run_session(params: StdioServerParameters, body: Callable) -> Any:
    return anyio.run(with_session, params, body)


async def list_tool_names(session: ClientSession) -> list[str]:
    listed = await session.list_tools()
    return [tool.name for tool in listed.tools]


async def call(session: ClientSession, tool: str, **arguments: Any) -> tuple[CallToolResult, dict[str, Any]]:
    result = await session.call_tool(tool, arguments)
    return result, parse_tool(result)


def dumped(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def assert_no_live_rpc_ids(payload: dict[str, Any]) -> None:
    blob = dumped(payload)
    assert "google_rpc_id" not in payload
    assert '"rpc_id"' not in blob
    for forbidden in FORBIDDEN_TOOL_NAMES:
        assert forbidden not in blob
    assert "google_finance_ds_" not in blob
