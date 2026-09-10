"""D1: revision-pinned reuse notices. Does not fetch Google."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "319760998e60d4b060fb993b3dc8db94364b019c"
LICENSE_SHA256 = "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
LEGAL_SHA256 = "51dac106bb00d1c896f8c04cc6e39211f715a4e13a13700f8057bc68594e4048"


def test_pinned_revision_constant_and_notice_file():
    from saudi_exchange_reports.google_finance import PINNED_REVISION

    assert PINNED_REVISION == PIN
    notice = (ROOT / "vendor" / "google-finance-mcp" / "NOTICE.md").read_text(encoding="utf-8")
    assert PIN in notice
    assert "v0.1.4" in notice
    assert "0.1.3" in notice


def test_license_is_gpl_v3_and_matches_draft_hash():
    path = ROOT / "vendor" / "google-finance-mcp" / "LICENSE"
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == LICENSE_SHA256
    text = data.decode("utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in text
    assert "Version 3, 29 June 2007" in text


def test_legal_md_is_usage_policy_not_data_license():
    path = ROOT / "vendor" / "google-finance-mcp" / "LEGAL.md"
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == LEGAL_SHA256
    text = data.decode("utf-8")
    assert "does not grant any license" in text.lower() or "does not grant any license" in text
    assert "local, personal" in text.lower()
    assert "hosted" in text.lower()


def test_vendored_client_imports_without_mcp_package():
    import google_finance_mcp
    from google_finance_mcp import GoogleFinanceClient
    from google_finance_mcp.client import parse_mapping_from_html

    assert GoogleFinanceClient is google_finance_mcp.GoogleFinanceClient
    assert callable(parse_mapping_from_html)
    import sys

    assert "mcp" not in sys.modules or "google_finance_mcp.server" not in sys.modules
