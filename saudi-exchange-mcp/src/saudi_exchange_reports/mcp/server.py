"""Product stdio MCP server. Not google_finance_mcp.server."""

from __future__ import annotations

import functools
from typing import Any

import anyio
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import CallToolRequest, ErrorData, INVALID_PARAMS, Tool

from saudi_exchange_reports.mcp.handlers import dispatch
from saudi_exchange_reports.mcp.runtime import apply_env_hook

SERVER_NAME = "saudi-exchange-mcp"
SERVER_VERSION = "0.1.0"

INSTRUCTIONS = (
    "Google Finance is primary for everyday company questions and structured tables. "
    "Saudi Exchange PDFs are for official reports, notes, and original evidence. "
    "Installing or enabling this server does not itself perform research; the host must call tools "
    "(installing MCP does not itself perform research). "
    "Unknown quote freshness is not real-time. Google tables are not audited filings. "
    "PDF page citations apply only to PDF-derived facts. "
    "Do not merge Google labels such as Net income with PDF Profit for the year. "
    "This server covers the documented Main Market pilot sample only "
    "(Saudi Aramco 2222 / sa-tdwl-2222 and Maaden 1211 / sa-tdwl-1211). "
    "Use is local, personal, and user-initiated."
)

COMPANY_PROPERTIES = {
    "query": {
        "type": "string",
        "description": "Company name or ticker (Arabic or English).",
    },
    "name": {"type": "string", "description": "Company name when split from ticker."},
    "ticker": {"type": "string", "description": "Pilot ticker such as 2222 or 1211."},
    "exchange": {
        "type": "string",
        "description": "Optional exchange. Foreign venues yield wrong_exchange.",
    },
}


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


PRODUCT_TOOLS = [
    Tool(
        name="lookup_company",
        description=(
            "Shared identity lookup (Arabic/English name and/or ticker) for the documented "
            "Saudi Exchange Main Market pilot sample. Returns both Saudi Exchange and Google "
            "Finance identifier blocks on a match. Does not silently pick among ambiguous or "
            "conflicting inputs."
        ),
        inputSchema=_schema(COMPANY_PROPERTIES),
    ),
    Tool(
        name="google_overview",
        description=(
            "Google Finance overview, quote, and labelled statistics for a matched pilot company. "
            "Unknown freshness is not real-time. Google tables are not audited filings."
        ),
        inputSchema=_schema(COMPANY_PROPERTIES),
    ),
    Tool(
        name="google_news",
        description=(
            "Google Finance security news feed with publisher, article URL, and publication time "
            "when present. Headlines/snippets are not full articles (read_status)."
        ),
        inputSchema=_schema(COMPANY_PROPERTIES),
    ),
    Tool(
        name="google_profile",
        description=(
            "Google Finance profile/about fields (description, website, CEO, founded, "
            "headquarters, employees, sector). Missing fields are listed as unavailable."
        ),
        inputSchema=_schema(COMPANY_PROPERTIES),
    ),
    Tool(
        name="google_earnings",
        description=(
            "Google Finance quarterly earnings actual versus estimate. Surprise is present only "
            "when supplied. article_summary remains null. Not an official filing."
        ),
        inputSchema=_schema(COMPANY_PROPERTIES),
    ),
    Tool(
        name="google_financials",
        description=(
            "Google Finance income statement, balance sheet, or cash flow for annual or quarterly "
            "frequency. Original Google labels only; balance sheet and cash flow row names may be "
            "unverified (display_label_gap). Not an audited Saudi Exchange filing."
        ),
        inputSchema=_schema(
            {
                **COMPANY_PROPERTIES,
                "statement": {
                    "type": "string",
                    "enum": [
                        "income_statement",
                        "balance_sheet",
                        "cash_flow",
                        "income",
                        "balance",
                        "cash",
                    ],
                },
                "frequency": {"type": "string", "enum": ["annual", "quarterly"]},
            },
            required=["statement", "frequency"],
        ),
    ),
    Tool(
        name="google_coverage",
        description=(
            "Google Finance coverage and gap classes for earnings and financial statements "
            "(supported, empty/unavailable, display-label unverified). Does not merge PDF figures."
        ),
        inputSchema=_schema(COMPANY_PROPERTIES),
    ),
    Tool(
        name="research_company",
        description=(
            "Google-only compose for a broad company question: lookup identity plus overview, news, "
            "profile, earnings, and financials with per-section coverage. Does not retrieve official PDFs."
        ),
        inputSchema=_schema(COMPANY_PROPERTIES),
    ),
    Tool(
        name="list_official_reports",
        description=(
            "List original financial statements and reports from Saudi Exchange (website listing, "
            "not an official API). Distinguishes annual/interim, language, and publication date. "
            "A cached listing is not proof that no newer report exists unless inspect_cache is set."
        ),
        inputSchema=_schema(
            {
                **COMPANY_PROPERTIES,
                "inspect_cache": {
                    "type": "boolean",
                    "description": "If true, inspect a labelled cache copy instead of re-fetching.",
                },
            }
        ),
    ),
    Tool(
        name="download_official_report",
        description=(
            "Download an original Saudi Exchange /Resources/fsPdf/ PDF into configured storage. "
            "Selects by period, report type, and language, or downloads a known URL. "
            "Does not invent filenames. Google tables are not returned as the filing."
        ),
        inputSchema=_schema(
            {
                **COMPANY_PROPERTIES,
                "period": {"type": "string", "description": "Reporting period such as 2025."},
                "report_type": {
                    "type": "string",
                    "enum": ["annual", "interim", "other"],
                    "description": "Report type. Default annual.",
                },
                "url": {
                    "type": "string",
                    "description": "Known /Resources/fsPdf/ URL. Optional; skips listing selection.",
                },
                "language": {"type": "string", "description": "en or ar. Default en."},
                "revalidate": {"type": "boolean"},
            },
            required=["period"],
        ),
    ),
    Tool(
        name="read_official_report",
        description=(
            "Read 1-based PDF pages from a stored original Saudi Exchange report. "
            "Methods are native, ocr, mixed, or unreadable. Page numbers are PDF indices."
        ),
        inputSchema=_schema(
            {
                "path": {"type": "string", "description": "Path inside configured storage (or extra allowed roots)."},
                "pages": {"type": "string", "description": "Page spec such as 13-18,19."},
                "page": {"type": "integer", "description": "Single start page (1-based)."},
                "page_to": {"type": "integer", "description": "Inclusive end page."},
            },
            required=["path"],
        ),
    ),
    Tool(
        name="search_official_report",
        description=(
            "Search extracted text of a stored original Saudi Exchange PDF. Hits include the original "
            "string, PDF page number, content hash, and method. Empty search is not_found, not zero."
        ),
        inputSchema=_schema(
            {
                "path": {"type": "string"},
                "query": {"type": "string"},
                "pages": {"type": "string"},
            },
            required=["path"],
        ),
    ),
    Tool(
        name="find_official_line_item",
        description=(
            "Find a labelled line in a stored original Saudi Exchange PDF. Returns original string, "
            "page, and parsed number when present. Missing is not_found, not zero."
        ),
        inputSchema=_schema(
            {
                "path": {"type": "string"},
                "label": {"type": "string"},
                "pages": {"type": "string"},
            },
            required=["path"],
        ),
    ),
]

TOOL_NAMES = frozenset(tool.name for tool in PRODUCT_TOOLS)

server = Server(SERVER_NAME, version=SERVER_VERSION, instructions=INSTRUCTIONS)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return list(PRODUCT_TOOLS)


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    payload = await anyio.to_thread.run_sync(functools.partial(dispatch, name, arguments or {}))
    return payload


def _wrap_unknown_tools() -> None:
    original = server.request_handlers[CallToolRequest]

    async def handler(req: CallToolRequest):
        name = req.params.name
        if name not in TOOL_NAMES:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}"))
        return await original(req)

    server.request_handlers[CallToolRequest] = handler


_wrap_unknown_tools()


async def serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(NotificationOptions(tools_changed=False)),
        )


def main(argv: list[str] | None = None) -> None:
    del argv
    apply_env_hook()
    anyio.run(serve)


if __name__ == "__main__":
    main()
