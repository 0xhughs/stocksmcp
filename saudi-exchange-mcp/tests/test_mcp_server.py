"""Slice 05: product stdio MCP protocol (scripted; no live Google)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from mcp.shared.exceptions import McpError

from tests.mcp_support import (
    FORBIDDEN_TOOL_NAMES,
    INSTRUCTION_PHRASES,
    REQUIRED_TOOLS,
    assert_no_live_rpc_ids,
    call,
    dumped,
    list_tool_names,
    run_session,
    server_params,
)

ROOT = Path(__file__).resolve().parents[1]


def _params(tmp_path: Path, hook: str = "mcp_hooks:install_full", extra=None):
    storage = tmp_path / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    return server_params(storage, hook=hook, extra=extra), storage


def test_tools_list_is_fixed_product_and_not_upstream(tmp_path: Path):
    params, _ = _params(tmp_path)

    async def body(session, init):
        assert init.capabilities.tools is not None
        instructions = init.instructions or ""
        folded = instructions
        for phrase in INSTRUCTION_PHRASES:
            assert phrase.casefold() in folded.casefold()
        names = await list_tool_names(session)
        for name in REQUIRED_TOOLS:
            assert name in names
        for forbidden in FORBIDDEN_TOOL_NAMES:
            assert forbidden not in names
        assert not any(n.startswith("google_finance_ds_") for n in names)
        assert "google_crosscheck" not in names
        listed = await session.list_tools()
        by_name = {t.name: t.description or "" for t in listed.tools}
        assert "Google Finance" in by_name["google_overview"]
        assert "Saudi Exchange" in by_name["list_official_reports"]
        assert "Google Finance" not in by_name["lookup_company"] or "shared" in by_name["lookup_company"].lower()
        assert "shared" in by_name["lookup_company"].lower() or "identity" in by_name["lookup_company"].lower()
        return names

    names = run_session(params, body)
    assert "lookup_company" in names


def test_stdout_of_initialize_is_jsonrpc_only(tmp_path: Path):
    params, _ = _params(tmp_path)
    env = dict(params.env or {})
    # Inherit a minimal PATH so the venv interpreter can start.
    env["PATH"] = os_path()
    proc = subprocess.Popen(
        [params.command, *params.args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=params.cwd,
        env={**_default_env(), **env},
        text=True,
    )
    assert proc.stdin is not None and proc.stdout is not None
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "slice05-test", "version": "0"},
        },
    }
    proc.stdin.write(json.dumps(init) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    proc.kill()
    proc.wait(timeout=5)
    message = json.loads(line)
    assert message["jsonrpc"] == "2.0"
    assert message["id"] == 1
    assert "result" in message
    assert message["result"]["capabilities"]["tools"]["listChanged"] is False


def os_path() -> str:
    import os

    return os.environ.get("PATH", "/usr/bin:/bin")


def _default_env() -> dict[str, str]:
    import os

    keep = ("HOME", "LOGNAME", "PATH", "SHELL", "TERM", "USER", "LANG", "LC_ALL")
    return {k: os.environ[k] for k in keep if k in os.environ}


@pytest.mark.parametrize(
    "arguments,company_id,quote_id",
    [
        ({"query": "2222"}, "sa-tdwl-2222", "2222:TADAWUL"),
        ({"query": "Saudi Aramco"}, "sa-tdwl-2222", "2222:TADAWUL"),
        ({"query": "Aramco"}, "sa-tdwl-2222", "2222:TADAWUL"),
        ({"query": "أرامكو"}, "sa-tdwl-2222", "2222:TADAWUL"),
        ({"query": "أرامكو السعودية"}, "sa-tdwl-2222", "2222:TADAWUL"),
        ({"query": "شركة الزيت العربية السعودية"}, "sa-tdwl-2222", "2222:TADAWUL"),
        ({"query": "1211"}, "sa-tdwl-1211", "1211:TADAWUL"),
        ({"query": "MAADEN"}, "sa-tdwl-1211", "1211:TADAWUL"),
        ({"query": "معادن"}, "sa-tdwl-1211", "1211:TADAWUL"),
        ({"name": "Saudi Aramco", "ticker": "2222"}, "sa-tdwl-2222", "2222:TADAWUL"),
    ],
)
def test_lookup_company_matched_identity_via_mcp(tmp_path: Path, arguments, company_id, quote_id):
    params, _ = _params(tmp_path)

    async def body(session, _init):
        _res, payload = await call(session, "lookup_company", **arguments)
        assert payload["status"] == "matched"
        company = payload["company"]
        assert company["company_id"] == company_id
        assert company["google_finance"]["quote_id"] == quote_id
        assert company["google_finance"]["verified"] is True
        assert company["google_finance"]["quote_id"] != "2222:SAU"
        assert company["google_finance"]["quote_id"] != "1211:SAU"
        assert company["saudi_exchange"]["company_symbol"]
        assert company["saudi_exchange"]["profile_url"]
        assert company["saudi_exchange"]["market"]
        return payload

    payload = run_session(params, body)
    assert payload["source"] == "shared_identity"


def test_lookup_identity_failures_are_structured_tool_results(tmp_path: Path):
    params, _ = _params(tmp_path)

    async def body(session, _init):
        cases = [
            ({"name": "Saudi Aramco", "ticker": "1211"}, "conflicting", 2),
            ({"query": "Saudi Arabian"}, "ambiguous", None),
            ({}, "unknown", 0),
            ({"query": "9999"}, "not_found", 0),
            ({"query": "2222", "exchange": "NASDAQ"}, "wrong_exchange", 0),
            ({"ticker": "2222", "exchange": "SAU"}, "wrong_exchange", 0),
        ]
        out = []
        for arguments, status, n_cand in cases:
            result, payload = await call(session, "lookup_company", **arguments)
            assert result.isError is False
            assert payload["status"] == status
            assert payload["company"] is None
            if n_cand is not None:
                assert len(payload["candidates"]) == n_cand
            out.append(status)
        return out

    assert run_session(params, body) == [
        "conflicting",
        "ambiguous",
        "unknown",
        "not_found",
        "wrong_exchange",
        "wrong_exchange",
    ]


def test_google_tools_return_shipped_fields_labelled_google(tmp_path: Path):
    params, _ = _params(tmp_path)

    async def body(session, _init):
        overview_r, overview = await call(session, "google_overview", query="ARAMCO")
        assert overview_r.isError is False
        assert overview["source"] == "google_finance"
        assert overview["source_label"] == "Google Finance"
        assert "google.com/finance" in overview["source_url"]
        assert overview["identity"]["ticker"] == "2222"
        assert overview["currency"] == "SAR"
        assert overview["last"] == pytest.approx(12.34)
        assert overview["is_realtime"] is False
        assert overview["retrieved_at"]
        assert "page_number" not in dumped(overview)
        assert "official_filing" not in dumped(overview)
        assert_no_live_rpc_ids(overview)
        if overview["last"] is None:
            assert "last" in overview["unavailable"]
        else:
            assert overview["last"] != 0 or "last" not in overview.get("unavailable", [])

        _n, news = await call(session, "google_news", query="ARAMCO")
        assert news["source"] == "google_finance"
        item = news["items"][0]
        assert item["publisher"]
        assert item["url"]
        assert item["read_status"] == "not_read"
        assert item["article_body"] is None

        _p, profile = await call(session, "google_profile", query="ARAMCO")
        assert profile["source"] == "google_finance"
        assert profile["description"]
        assert profile["website"]
        assert "ceo" in profile

        _e, earnings = await call(session, "google_earnings", query="ARAMCO")
        assert earnings["source"] == "google_finance"
        assert earnings["article_summary"] is None
        period = earnings["periods"][0]
        assert period["revenue_actual"]["kind"]
        assert period["revenue_estimate"]["kind"]
        assert period["eps_actual"]["availability"] in {"present", "unavailable"}

        statements = []
        for statement, frequency in (
            ("income_statement", "annual"),
            ("income_statement", "quarterly"),
            ("balance_sheet", "annual"),
            ("cash_flow", "quarterly"),
        ):
            _f, fin = await call(
                session, "google_financials", query="ARAMCO", statement=statement, frequency=frequency
            )
            assert fin["source"] == "google_finance"
            assert fin["statement"] == statement
            assert fin["frequency"] == frequency
            if statement == "income_statement":
                assert fin["periods"]
                labels = [row["label"] for period in fin["periods"] for row in period["rows"]]
                assert "Revenue" in labels or "Net income" in labels
                assert "Profit for the year" not in labels
            else:
                assert fin["display_label_gap"] is True
            statements.append(fin["statement"])

        _c, coverage = await call(session, "google_coverage", query="ARAMCO")
        assert coverage["source"] == "google_finance"
        sections = {(s["section"], s["frequency"]): s["status"] for s in coverage["sections"]}
        assert sections[("income_statement", "quarterly")]
        return overview["source"]

    assert run_session(params, body) == "google_finance"


def test_google_tools_do_not_silently_resolve_conflicts(tmp_path: Path):
    params, _ = _params(tmp_path)

    async def body(session, _init):
        result, payload = await call(session, "google_overview", name="Saudi Aramco", ticker="1211")
        assert result.isError is False
        assert payload["status"] == "conflicting"
        assert payload.get("last") is None
        assert payload["company"] is None
        return payload["status"]

    assert run_session(params, body) == "conflicting"


def test_report_tools_list_download_read_search(tmp_path: Path):
    params, storage = _params(tmp_path)

    async def body(session, _init):
        _l, listing = await call(session, "list_official_reports", query="MAADEN")
        assert listing["source"] == "saudi_exchange"
        assert listing["from_cache"] is False
        assert listing["unavailable"] is False
        assert listing["reports"]
        report = listing["reports"][0]
        assert report["period"]
        assert report["report_type"] in {"annual", "interim", "other"}
        assert report["language"]
        assert report["source_url"].startswith("https://www.saudiexchange.sa/Resources/fsPdf/")
        assert "freshness_note" in listing

        _d, downloaded = await call(
            session,
            "download_official_report",
            query="MAADEN",
            period="2025",
            report_type="annual",
            language="en",
        )
        assert downloaded["source"] == "saudi_exchange"
        assert downloaded["status"] == "downloaded"
        assert downloaded["content_hash"]
        assert downloaded["local_path"]
        assert downloaded["retrieved_at"]
        pdf_path = Path(downloaded["local_path"])
        assert pdf_path.is_relative_to(storage) or str(pdf_path).startswith(str(storage))

        _r, read = await call(session, "read_official_report", path=str(pdf_path), pages="1")
        assert read["source"] == "saudi_exchange"
        page = read["pages"][0]
        assert page["page_number"] == 1
        assert page["method"] in {"native", "ocr", "mixed", "unreadable"}
        assert "share capital" in page["text"].lower() or "mining" in page["text"].lower()

        _s, search = await call(
            session, "search_official_report", path=str(pdf_path), query="share capital", pages="1"
        )
        assert search["source"] == "saudi_exchange"
        assert search["status"] == "found"
        assert search["hits"][0]["page_number"] == 1
        assert search["hits"][0]["original"]

        _empty, empty = await call(session, "search_official_report", path=str(pdf_path), query="", pages="1")
        assert empty["status"] == "not_found"
        return downloaded["status"]

    assert run_session(params, body) == "downloaded"


def test_four_prompt_classes_on_one_scripted_connection(tmp_path: Path):
    params, _ = _params(tmp_path)

    async def body(session, init):
        names = await list_tool_names(session)
        assert set(REQUIRED_TOOLS) <= set(names)

        _ar, ar = await call(session, "lookup_company", query="أرامكو")
        _en, en = await call(session, "lookup_company", query="Saudi Aramco")
        assert ar["status"] == en["status"] == "matched"
        assert ar["company"]["company_id"] == "sa-tdwl-2222"

        _broad, broad = await call(session, "research_company", query="ARAMCO")
        assert broad["source"] == "google_finance"
        assert broad["pulled_official_pdfs"] is False
        for key in ("overview", "news", "profile", "earnings"):
            assert key in broad["sections"]
            assert broad["sections"][key]["source"] == "google_finance"
        is_q = broad["sections"]["income_statement_quarterly"]
        assert is_q["source"] == "google_finance"
        assert is_q.get("periods") or is_q.get("unavailable")
        for key in ("balance_sheet_annual", "cash_flow_annual"):
            section = broad["sections"][key]
            assert section["source"] == "google_finance"
            assert section.get("display_label_gap") or section.get("periods") or section.get("unavailable")
        assert "page_number" not in dumped(broad)

        _ov, overview = await call(session, "google_overview", query="ARAMCO")
        assert overview["last"] is not None
        assert overview["currency"]
        assert overview["source_url"]
        assert overview["retrieved_at"]
        assert overview["freshness"] in {"quoted_at", "unknown"}
        await call(session, "google_news", query="ARAMCO")
        await call(session, "google_profile", query="ARAMCO")
        await call(session, "google_earnings", query="ARAMCO")
        await call(session, "google_financials", query="ARAMCO", statement="income_statement", frequency="annual")
        await call(session, "google_financials", query="ARAMCO", statement="balance_sheet", frequency="annual")
        await call(session, "google_financials", query="ARAMCO", statement="cash_flow", frequency="quarterly")

        _list, listing = await call(session, "list_official_reports", query="MAADEN")
        assert listing["source"] == "saudi_exchange"
        _dl, downloaded = await call(
            session, "download_official_report", query="MAADEN", period="2025", report_type="annual", language="en"
        )
        _rd, read = await call(session, "read_official_report", path=downloaded["local_path"], pages="1")
        _sr, search = await call(
            session, "search_official_report", path=downloaded["local_path"], query="share capital", pages="1"
        )
        assert search["hits"]
        assert "Net income" not in dumped(search)

        _combo_g, g = await call(session, "google_overview", query="2222")
        _combo_s, s = await call(
            session, "search_official_report", path=downloaded["local_path"], query="share capital", pages="1"
        )
        assert g["source"] == "google_finance"
        assert s["source"] == "saudi_exchange"
        assert g["identity"]["ticker"] == "2222"
        return {
            "init": bool(init.instructions),
            "arabic": ar["company"]["ticker"],
            "english": en["company"]["ticker"],
            "broad": "overview" in broad["sections"],
            "official": search["status"],
            "combined": (g["source"], s["source"]),
        }

    evidence = run_session(params, body)
    assert evidence["arabic"] == "2222"
    assert evidence["combined"] == ("google_finance", "saudi_exchange")


def test_google_failure_does_not_disable_report_tools(tmp_path: Path):
    params, _ = _params(tmp_path, hook="mcp_hooks:install_google_fail")

    async def body(session, _init):
        g_result, google = await call(session, "google_overview", query="ARAMCO")
        assert google["status"] == "unavailable"
        assert google["source"] == "google_finance"
        _l, listing = await call(session, "list_official_reports", query="MAADEN")
        assert listing["unavailable"] is False
        assert listing["reports"]
        return listing["source"]

    assert run_session(params, body) == "saudi_exchange"


def test_report_failure_does_not_disable_google_tools(tmp_path: Path):
    params, _ = _params(tmp_path, hook="mcp_hooks:install_report_fail")

    async def body(session, _init):
        _l, listing = await call(session, "list_official_reports", query="MAADEN")
        assert listing["unavailable"] is True
        _o, overview = await call(session, "google_overview", query="ARAMCO")
        assert overview["source"] == "google_finance"
        assert overview["last"] == pytest.approx(12.34)
        return overview["source"]

    assert run_session(params, body) == "google_finance"


def test_google_handlers_do_not_write_storage(tmp_path: Path):
    params, storage = _params(tmp_path)

    async def body(session, _init):
        await call(session, "google_overview", query="ARAMCO")
        await call(session, "research_company", query="ARAMCO")
        return [p.relative_to(storage).as_posix() for p in storage.rglob("*") if p.is_file()]

    files = run_session(params, body)
    assert files == []


def test_report_handlers_do_not_construct_live_google(tmp_path: Path):
    sentinel = tmp_path / "live-google-sentinel"
    params, _ = _params(
        tmp_path,
        hook="mcp_hooks:install_reports_isolation",
        extra={"SAUDI_MCP_SENTINEL": str(sentinel)},
    )

    async def body(session, _init):
        _l, listing = await call(session, "list_official_reports", query="1211")
        assert listing["reports"]
        return listing["source"]

    assert run_session(params, body) == "saudi_exchange"
    assert not sentinel.exists()


def test_invalid_pdf_and_unsafe_path_via_mcp(tmp_path: Path):
    params, _ = _params(tmp_path, hook="mcp_hooks:install_invalid_pdf")

    async def body(session, _init):
        _d, downloaded = await call(
            session, "download_official_report", query="MAADEN", period="2025", report_type="annual", language="en"
        )
        assert downloaded["status"] == "failed"
        assert downloaded["record"] is None
        assert downloaded["error_type"] == "InvalidPdf"

        outside = tmp_path / "outside.pdf"
        outside.write_bytes(b"%PDF-1.4 fake")
        result, unsafe = await call(session, "read_official_report", path=str(outside), pages="1")
        assert unsafe["error_type"] == "UnsafeDestination" or result.isError
        return downloaded["status"]

    assert run_session(params, body) == "failed"


def test_missing_period_is_unavailable_via_mcp(tmp_path: Path):
    params, _ = _params(tmp_path)

    async def body(session, _init):
        _d, downloaded = await call(
            session, "download_official_report", query="MAADEN", period="1999", report_type="annual", language="en"
        )
        assert downloaded["status"] == "unavailable"
        assert downloaded.get("record") is None
        return downloaded["status"]

    assert run_session(params, body) == "unavailable"


def test_unknown_tool_is_protocol_error(tmp_path: Path):
    params, _ = _params(tmp_path)

    async def body(session, _init):
        with pytest.raises(McpError):
            await session.call_tool("google_finance_call_rpc", {})
        return True

    assert run_session(params, body) is True


def test_cursor_mcp_example_parses(tmp_path: Path):
    del tmp_path
    path = ROOT / "evidence" / "05-hybrid-mcp" / "cursor-mcp.json.example"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    server = next(iter(data["mcpServers"].values()))
    assert "command" in server
    assert "args" in server
    assert "-m" in server["args"]
    assert "saudi_exchange_reports.mcp" in server["args"]
    assert "google_finance_mcp" not in json.dumps(data)


def test_importing_google_client_still_skips_upstream_server():
    import importlib
    import sys

    sys.modules.pop("google_finance_mcp.server", None)
    from google_finance_mcp.client import GoogleFinanceClient

    assert GoogleFinanceClient is not None
    assert "google_finance_mcp.server" not in sys.modules
    product = importlib.import_module("saudi_exchange_reports.mcp")
    assert product.__name__ == "saudi_exchange_reports.mcp"
    assert "google_finance_mcp.server" not in sys.modules


MAADEN_HASH = "d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e"
MAADEN_FS = ROOT / "storage" / "reports" / "1211" / f"{MAADEN_HASH}.pdf"


@pytest.mark.stored_pdf
@pytest.mark.skipif(not MAADEN_FS.exists(), reason="gitignored Maaden 2025 annual English FS PDF is not in storage")
def test_stored_maaden_read_search_via_mcp(tmp_path: Path):
    extra = {"SAUDI_MCP_EXTRA_ROOTS": str(MAADEN_FS.parents[1])}
    params, _ = _params(tmp_path, extra=extra)
    # Point storage at the real reports root so the stored original is in-bounds.
    params = server_params(MAADEN_FS.parents[1], hook="mcp_hooks:install_full", extra=extra)

    async def body(session, _init):
        _r, read = await call(session, "read_official_report", path=str(MAADEN_FS), pages="19")
        assert read["content_hash"] == MAADEN_HASH
        page = read["pages"][0]
        assert page["page_number"] == 19
        assert page["method"] == "native"
        assert "Notes to the consolidated financial statements" in page["text"]
        _s, search = await call(
            session, "search_official_report", path=str(MAADEN_FS), query="share capital", pages="19"
        )
        assert search["status"] == "found"
        assert any(h["page_number"] == 19 for h in search["hits"])
        assert search["source"] == "saudi_exchange"
        return page["method"]

    assert run_session(params, body) == "native"
