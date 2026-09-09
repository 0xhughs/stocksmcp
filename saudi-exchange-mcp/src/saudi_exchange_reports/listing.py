"""Parse Saudi Exchange Financial Statements and Reports tables and select a report."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlparse

from saudi_exchange_reports.errors import DisallowedRedirect
from saudi_exchange_reports.models import (
    CompanyIdentity,
    FinancialReport,
    ReportListing,
    ReportSelection,
    ReportType,
)

FSPDF_HOSTS = frozenset({"www.saudiexchange.sa", "saudiexchange.sa"})
FSPDF_PATH_PREFIX = "/Resources/fsPdf/"
PROFILE_HOST = "www.saudiexchange.sa"
# Website AJAX used by the company-profile Financial Statements tab (stmtType=6).
# This is not a documented official API.
STATEMENTS_TAB_STATEMENT_TYPE = "6"
STATEMENTS_TAB_REPORT_TYPE = "0"

_BASE_HREF_RE = re.compile(r'<base[^>]+href=["\']([^"\']+)["\']', re.I)
_TAB_REL_RE = re.compile(
    r"url:\s*['\"]([^'\"]*statementsTabData[^'\"]*)['\"]",
    re.I,
)
_LOCALE_RE = re.compile(
    r'<input[^>]*id=["\']requestLocale["\'][^>]*value=["\']([^"\']+)["\']',
    re.I,
)
_LOCALE_RE_ALT = re.compile(
    r'<input[^>]*value=["\']([^"\']+)["\'][^>]*id=["\']requestLocale["\']',
    re.I,
)

_LANG_FROM_TEXT = {
    "english": "en",
    "en": "en",
    "eng": "en",
    "arabic": "ar",
    "ar": "ar",
    "arb": "ar",
    "عربي": "ar",
    "الإنجليزية": "en",
    "العربية": "ar",
}

_ANNUAL_WORDS = ("annual", "year", "fy", "سنوي")
_INTERIM_WORDS = ("interim", "quarter", "q1", "q2", "q3", "q4", "نصف", "ربع", "أولي")
_OTHER_SECTIONS = ("board report", "esg report", "sustainability")


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.anchors: list[tuple[str, str]] = []
        self._in_th = False
        self._in_td = False
        self._cell_text: list[str] = []
        self.rows: list[list[str]] = []
        self._row: list[str] = []
        self._row_hrefs: list[str] = []
        self.row_links: list[list[tuple[str, str]]] = []
        self._row_link_buf: list[tuple[str, str]] = []
        self._current_section = "Financial Statements"
        self.sections_by_row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: v or "" for k, v in attrs}
        if tag == "a":
            self._current_href = ad.get("href") or None
            self._current_text = []
        elif tag == "tr":
            self._row = []
            self._row_link_buf = []
        elif tag == "th":
            self._in_th = True
            self._cell_text = []
        elif tag == "td":
            self._in_td = True
            self._cell_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href:
            text = " ".join(self._current_text).strip()
            self.anchors.append((self._current_href, text))
            self._row_link_buf.append((self._current_href, text))
            self._current_href = None
            self._current_text = []
        elif tag in {"td", "th"}:
            text = " ".join(self._cell_text).strip()
            self._row.append(text)
            if tag == "th":
                lowered = text.casefold()
                if lowered in {
                    "financial statements",
                    "xbrl",
                    "board report",
                    "esg report",
                } or "financial statements" in lowered:
                    if lowered != "financial statements and reports":
                        self._current_section = text
            self._in_td = False
            self._in_th = False
            self._cell_text = []
        elif tag == "tr":
            if self._row or self._row_link_buf:
                self.rows.append(self._row)
                self.row_links.append(self._row_link_buf)
                self.sections_by_row.append(self._current_section)

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)
        if self._in_td or self._in_th:
            self._cell_text.append(data)


def _absolute_fs_url(href: str) -> str | None:
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("/"):
        href = urljoin("https://www.saudiexchange.sa/", href)
    parsed = urlparse(href)
    if parsed.scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower()
    if host not in FSPDF_HOSTS:
        return None
    if not parsed.path.startswith(FSPDF_PATH_PREFIX):
        return None
    if not parsed.path.lower().endswith(".pdf"):
        return None
    return href


def _request_locale(html: str) -> str:
    match = _LOCALE_RE.search(html) or _LOCALE_RE_ALT.search(html)
    if not match:
        return "en"
    value = match.group(1).strip().lower()
    if value.startswith("ar"):
        return "ar"
    if value.startswith("en"):
        return "en"
    return "en"


def statements_index_url(html: str, *, page_url: str, symbol: str) -> str | None:
    """Build the Financial Statements tab GET URL from untrusted profile HTML.

    Observed browser behaviour: GET relative ``statementsTabData`` with
    ``statementType=6``. This is website AJAX, not an official public API.
    """
    match = _TAB_REL_RE.search(html)
    if not match:
        return None
    rel = match.group(1).strip()
    if rel.lower().startswith("javascript:"):
        return None
    base_match = _BASE_HREF_RE.search(html)
    base = (base_match.group(1).strip() if base_match else "") or page_url
    tab = urljoin(base, rel)
    parsed = urlparse(tab)
    if parsed.scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower()
    if host not in FSPDF_HOSTS:
        return None
    query = urlencode(
        {
            "statementType": STATEMENTS_TAB_STATEMENT_TYPE,
            "reportType": STATEMENTS_TAB_REPORT_TYPE,
            "requestLocale": _request_locale(html),
            "symbol": symbol,
        }
    )
    sep = "&" if parsed.query else "?"
    return tab + sep + query


def report_from_fspdf_url(
    company: CompanyIdentity,
    url: str,
    *,
    period: str | None = None,
    report_type: ReportType | None = None,
    language: str | None = None,
    title: str | None = None,
) -> FinancialReport:
    abs_url = _absolute_fs_url(url)
    if not abs_url:
        raise DisallowedRedirect(f"Not a verified /Resources/fsPdf/ URL: {url}")
    language = language or _language_from(abs_url, "")
    period = period or _period_from_row([], abs_url)
    report_type = report_type or _type_from("Financial Statements", [], abs_url)
    pub, pub_missing = _publication_date([], abs_url)
    return FinancialReport(
        title=title or _title_from("Financial Statements", [], report_type, language, period),
        period=period,
        report_type=report_type,
        language=language,
        source_url=abs_url,
        download_url=abs_url,
        publication_date=pub,
        publication_date_unavailable=pub_missing,
        section="Financial Statements",
        company_ticker=company.ticker,
    )


def _language_from(href: str, link_text: str) -> str:
    text = link_text.strip().casefold()
    if text in _LANG_FROM_TEXT:
        return _LANG_FROM_TEXT[text]
    name = href.rsplit("/", 1)[-1]
    m = re.search(r"_(en|eng|ar|arb)(?:\.pdf)?$", name, re.I)
    if m:
        token = m.group(1).lower()
        return "ar" if token.startswith("ar") else "en"
    return "und"


def _period_from_row(cells: list[str], href: str) -> str:
    for cell in cells:
        if re.fullmatch(r"\d{4}", cell.strip()):
            return cell.strip()
        m = re.search(r"(20\d{2})\s*Q([1-4])", cell, re.I)
        if m:
            return f"{m.group(1)} Q{m.group(2)}"
        m = re.search(r"Q([1-4])\s*(20\d{2})", cell, re.I)
        if m:
            return f"{m.group(2)} Q{m.group(1)}"
        if re.search(r"20\d{2}", cell) and re.search(r"q[1-4]|interim|ربع", cell, re.I):
            year = re.search(r"20\d{2}", cell)
            q = re.search(r"q\s*([1-4])", cell, re.I)
            if year and q:
                return f"{year.group(0)} Q{q.group(1)}"
            if year:
                return year.group(0)
    fname = href.rsplit("/", 1)[-1]
    m = re.search(r"_(\d{4})-(\d{2})-\d{2}_", fname)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        # Filing-date heuristic is not the reporting period; leave filename year
        # only when no better cell text exists.
        if month <= 4:
            return str(year - 1)
        return str(year)
    return "unknown"


def _publication_date(cells: list[str], href: str) -> tuple[str | None, bool]:
    for cell in cells:
        m = re.fullmatch(r"(20\d{2}-\d{2}-\d{2})", cell.strip())
        if m:
            return m.group(1), False
    fname = href.rsplit("/", 1)[-1]
    m = re.search(r"_(\d{4}-\d{2}-\d{2})_", fname)
    if m:
        return m.group(1), False
    return None, True


def _type_from(section: str, cells: list[str], href: str) -> ReportType:
    blob = " ".join([section, *cells, href]).casefold()
    if any(word in blob for word in _OTHER_SECTIONS) or "board" in section.casefold():
        return ReportType.OTHER
    if any(word in blob for word in _INTERIM_WORDS) or re.search(r"q[1-4]", blob):
        return ReportType.INTERIM
    if any(word in blob for word in _ANNUAL_WORDS):
        return ReportType.ANNUAL
    fname = href.rsplit("/", 1)[-1]
    # Observed pattern: {issuer}_0_{date}_Lang.pdf is commonly the annual pack.
    if re.search(r"^\d+_0_", fname):
        return ReportType.ANNUAL
    return ReportType.OTHER


def _title_from(section: str, cells: list[str], report_type: ReportType, language: str, period: str) -> str:
    lang_label = {"en": "English", "ar": "Arabic"}.get(language, language)
    type_label = report_type.value
    extra = " ".join(c for c in cells if c and not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", c))
    extra = extra.strip()
    if extra:
        return f"{section}: {extra} ({lang_label})"
    return f"{section} {type_label} {period} ({lang_label})"


def parse_report_index_html(html: str, company: CompanyIdentity) -> tuple[FinancialReport, ...]:
    """Parse untrusted HTML as data. Never execute it."""
    parser = _AnchorCollector()
    parser.feed(html)
    reports: list[FinancialReport] = []
    seen: set[str] = set()
    for cells, links, section in zip(parser.rows, parser.row_links, parser.sections_by_row, strict=False):
        for href, text in links:
            url = _absolute_fs_url(href)
            if not url or url in seen:
                continue
            seen.add(url)
            language = _language_from(url, text)
            period = _period_from_row(cells, url)
            pub, pub_missing = _publication_date(cells, url)
            report_type = _type_from(section, cells, url)
            reports.append(
                FinancialReport(
                    title=_title_from(section, cells, report_type, language, period),
                    period=period,
                    report_type=report_type,
                    language=language,
                    source_url=url,
                    download_url=url,
                    publication_date=pub,
                    publication_date_unavailable=pub_missing,
                    section=section,
                    company_ticker=company.ticker,
                )
            )
    return tuple(reports)


def list_reports(
    company: CompanyIdentity,
    *,
    html: str,
    source_url: str | None = None,
    from_cache: bool = False,
    retrieved_at: str | None = None,
) -> ReportListing:
    reports = parse_report_index_html(html, company)
    if not reports:
        return ReportListing(
            reports=(),
            from_cache=from_cache,
            retrieved_at=retrieved_at,
            unavailable=True,
            reason="No financial-statement PDF links were present in the supplied index.",
            source_url=source_url,
        )
    return ReportListing(
        reports=reports,
        from_cache=from_cache,
        retrieved_at=retrieved_at,
        unavailable=False,
        reason="Listed reports from the Financial Statements and Reports index.",
        source_url=source_url,
    )


def select_report(
    reports: tuple[FinancialReport, ...] | list[FinancialReport],
    *,
    period: str,
    report_type: ReportType | None = None,
    language: str | None = None,
) -> ReportSelection:
    period_q = period.strip()
    matches = [r for r in reports if r.period == period_q or r.period.startswith(period_q)]
    if report_type is not None:
        matches = [r for r in matches if r.report_type is report_type]
    if language is not None:
        matches = [r for r in matches if r.language == language.casefold()]
    if not matches:
        return ReportSelection(
            status="unavailable",
            report=None,
            candidates=(),
            reason=f"No report in the listing matches period {period_q!r}.",
        )
    if len(matches) > 1:
        return ReportSelection(
            status="ambiguous",
            report=None,
            candidates=tuple(matches),
            reason="Multiple reports match the requested filters; refusing to pick one.",
        )
    return ReportSelection(
        status="selected",
        report=matches[0],
        candidates=tuple(matches),
        reason="Selected a single matching report.",
    )
