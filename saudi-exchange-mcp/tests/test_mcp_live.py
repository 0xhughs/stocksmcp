"""Opt-in live MCP session. Skipped unless --live-google / SAUDI_LIVE_GOOGLE=1."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.mcp_support import REQUIRED_TOOLS, call, list_tool_names, run_session, server_params

ROOT = Path(__file__).resolve().parents[1]
MAADEN_HASH = "d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e"
MAADEN_FS = ROOT / "storage" / "reports" / "1211" / f"{MAADEN_HASH}.pdf"
MAADEN_URL = "https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf"

pytestmark = [pytest.mark.live_google, pytest.mark.live_mcp]


def test_live_mcp_four_prompt_classes_one_connection(tmp_path):
    storage = ROOT / "storage" / "reports"
    params = server_params(storage, live=True)

    async def body(session, init):
        names = await list_tool_names(session)
        assert set(REQUIRED_TOOLS) <= set(names)
        assert init.instructions

        _ar, arabic = await call(session, "lookup_company", query="أرامكو")
        _en, english = await call(session, "lookup_company", query="Saudi Aramco")
        assert arabic["status"] == english["status"] == "matched"
        assert arabic["company"]["google_finance"]["quote_id"] == "2222:TADAWUL"

        _ov, overview = await call(session, "google_overview", query="ARAMCO")
        assert overview["source"] == "google_finance"
        assert overview["identity"]["ticker"] == "2222"
        assert overview["currency"]
        assert overview["source_url"]
        assert overview["retrieved_at"]
        assert overview["is_realtime"] is False
        if overview["last"] is None:
            assert "last" in overview["unavailable"]
        _news, news = await call(session, "google_news", query="ARAMCO")
        assert news["source"] == "google_finance"
        _pr, profile = await call(session, "google_profile", query="ARAMCO")
        assert profile["source"] == "google_finance"
        _ea, earnings = await call(session, "google_earnings", query="ARAMCO")
        assert earnings["source"] == "google_finance"
        _isq, income_q = await call(
            session, "google_financials", query="ARAMCO", statement="income_statement", frequency="quarterly"
        )
        _isa, income_a = await call(
            session, "google_financials", query="ARAMCO", statement="income_statement", frequency="annual"
        )
        _bs, balance = await call(
            session, "google_financials", query="ARAMCO", statement="balance_sheet", frequency="annual"
        )
        _cf, cash = await call(
            session, "google_financials", query="ARAMCO", statement="cash_flow", frequency="annual"
        )
        assert income_q["source"] == income_a["source"] == "google_finance"
        if not income_q["periods"]:
            assert "quarterly" in income_q["unavailable"] or "income_statement" in income_q["unavailable"]
        assert balance["display_label_gap"] or balance["periods"]
        assert cash["display_label_gap"] or cash["periods"] or cash["unavailable"]

        listing_status = "skipped_live_listing"
        listing_reason = None
        try:
            _ls, listing = await call(session, "list_official_reports", query="MAADEN")
            listing_status = "unavailable" if listing.get("unavailable") else "ok"
            listing_reason = listing.get("reason")
        except Exception as exc:  # live website may fail; read/search still required
            listing_status = f"error:{type(exc).__name__}"
            listing_reason = str(exc)

        if not MAADEN_FS.exists():
            pytest.skip("stored Maaden FS missing; retrieve with slice 01 CLI first")

        _rd, read = await call(session, "read_official_report", path=str(MAADEN_FS), pages="19")
        assert read["source"] == "saudi_exchange"
        assert read["content_hash"] == MAADEN_HASH
        assert read["pages"][0]["page_number"] == 19
        _sr, search = await call(
            session, "search_official_report", path=str(MAADEN_FS), query="share capital", pages="19"
        )
        assert search["status"] == "found"
        assert any(h["page_number"] == 19 for h in search["hits"])

        _cg, g = await call(session, "google_overview", query="2222")
        _cs, s = await call(
            session, "search_official_report", path=str(MAADEN_FS), query="share capital", pages="19"
        )
        assert g["source"] == "google_finance"
        assert s["source"] == "saudi_exchange"
        return {
            "arabic": arabic["company"]["ticker"],
            "overview_currency": bool(overview["currency"]),
            "listing_status": listing_status,
            "listing_reason": listing_reason,
            "search": search["status"],
            "combined": True,
            "url_known": MAADEN_URL,
        }

    evidence = run_session(params, body)
    assert evidence["arabic"] == "2222"
    assert evidence["combined"] is True
    assert evidence["search"] == "found"
    del tmp_path
