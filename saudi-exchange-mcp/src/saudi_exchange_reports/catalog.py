"""Documented pilot sample for slice 01.

Names, tickers, markets, and profile URLs below were observed on
https://www.saudiexchange.sa company-profile pages on 2026-09-09.
Google Finance mappings are verified Tadawul quote identifiers (slice 03).
"""

from __future__ import annotations

from saudi_exchange_reports.models import (
    CompanyIdentity,
    GoogleFinanceMapping,
    SaudiExchangeIdentifiers,
)

PROFILE_PATH = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/"
    "company-profile-main/"
)
# Fixed WebSphere rewrite token observed on live company-profile URLs
# (same token for 2222 and 1211). Company selection is ?companySymbol=.
PROFILE_TOKEN = (
    "!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziTR3NDIw8LAz83d2MXA0C3SydAl1c3Q0N"
    "vE30I4EKzBEKDMKcTQzMDPxN3H19LAzdTU31w8syU8v1wwkpK8hOMgUA-oskdg!!/"
)


def profile_url(symbol: str) -> str:
    return f"{PROFILE_PATH}{PROFILE_TOKEN}?companySymbol={symbol}"


ARAMCO = CompanyIdentity(
    company_id="sa-tdwl-2222",
    english_name="Saudi Arabian Oil Co.",
    arabic_name="شركة الزيت العربية السعودية",
    ticker="2222",
    exchange="Saudi Exchange Main Market",
    aliases=(
        "Saudi Aramco",
        "SAUDI ARAMCO",
        "Aramco",
        "أرامكو السعودية",
        "أرامكو",
        "Saudi Arabian Oil Company",
        "Saudi Arabian Oil",
    ),
    saudi_exchange=SaudiExchangeIdentifiers(
        company_symbol="2222",
        profile_url=profile_url("2222"),
        market="Main Market",
        # Observed on the Aramco company profile: /Resources/pdfs/1541_ByLaw1.pdf
        issuer_id="1541",
    ),
    google_finance=GoogleFinanceMapping(
        quote_symbol="2222",
        exchange="TADAWUL",
        quote_id="2222:TADAWUL",
        quote_url="https://www.google.com/finance/quote/2222:TADAWUL",
        verified=True,
    ),
)

MAADEN = CompanyIdentity(
    company_id="sa-tdwl-1211",
    english_name="Saudi Arabian Mining Co.",
    arabic_name="شركة التعدين العربية السعودية",
    ticker="1211",
    exchange="Saudi Exchange Main Market",
    aliases=(
        "MAADEN",
        "Maaden",
        "معادن",
        "Saudi Arabian Mining",
        "Saudi Arabian Mining Company",
    ),
    saudi_exchange=SaudiExchangeIdentifiers(
        company_symbol="1211",
        profile_url=profile_url("1211"),
        market="Main Market",
        # Observed on Maaden company profile: /Resources/pdfs/370_ByLaw2.pdf
        # and on the 2025 English annual-report PDF URL
        # https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf
        issuer_id="370",
    ),
    google_finance=GoogleFinanceMapping(
        quote_symbol="1211",
        exchange="TADAWUL",
        quote_id="1211:TADAWUL",
        quote_url="https://www.google.com/finance/quote/1211:TADAWUL",
        verified=True,
    ),
)

PILOT_COMPANIES: tuple[CompanyIdentity, ...] = (ARAMCO, MAADEN)

SAUDI_EXCHANGE_NAMES = frozenset(
    {
        "saudi exchange",
        "saudi exchange main market",
        "tadawul",
        "tdwl",
        "main market",
        "tasi",
    }
)

FOREIGN_EXCHANGES = frozenset(
    {
        "nasdaq",
        "nyse",
        "amex",
        "lse",
        "hkex",
        "tyo",
        "euronext",
        "tsx",
        "asx",
    }
)
