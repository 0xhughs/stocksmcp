"""Dual-provenance comparison of Google tables against official PDF facts.

Google figures are never treated as the audited original. PDF page citations
apply only to PDF-derived facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from saudi_exchange_reports.google_finance.types import FinancialsResult, StatementPeriod
from saudi_exchange_reports.reading import ExtractedDocument, extract_report, find_line_item, parse_number, search_extracted


@dataclass(frozen=True)
class PdfFact:
    label: str
    original: str
    value: float | None
    page: int
    frequency: str = "annual"


@dataclass(frozen=True)
class ComparisonPair:
    pdf_label: str
    pdf_original: str | None
    pdf_value: float | None
    pdf_page: int | None
    google_label: str | None
    google_value: float | None
    google_label_status: str
    outcome: str
    reason: str
    google_source: str
    pdf_source: str
    duration_google: str | None = None
    duration_pdf: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdf_label": self.pdf_label,
            "pdf_original": self.pdf_original,
            "pdf_value": self.pdf_value,
            "pdf_page": self.pdf_page,
            "google_label": self.google_label,
            "google_value": self.google_value,
            "google_label_status": self.google_label_status,
            "outcome": self.outcome,
            "reason": self.reason,
            "google_source": self.google_source,
            "pdf_source": self.pdf_source,
            "duration_google": self.duration_google,
            "duration_pdf": self.duration_pdf,
        }


def _close(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return False
    if abs(left) < 10 and abs(right) < 10:
        return abs(left - right) < 0.005
    return abs(left - right) < 0.51


def _period_2025(result: FinancialsResult) -> StatementPeriod | None:
    for period in result.periods:
        if period.year == 2025:
            return period
    return result.periods[0] if result.periods else None


def _labeled_row(period: StatementPeriod | None, label: str):
    if period is None:
        return None
    for row in period.rows:
        if row.label == label:
            return row
    return None


def _unverified_with_value(period: StatementPeriod | None, value: float | None):
    if period is None or value is None:
        return None
    for row in period.rows:
        if row.label_status == "unverified" and _close(row.value, value):
            return row
    return None


def _pair(
    *,
    pdf: PdfFact | None,
    pdf_label: str,
    google_label: str | None,
    google_value: float | None,
    google_label_status: str,
    outcome: str,
    reason: str,
    duration_google: str | None,
    duration_pdf: str = "annual",
) -> ComparisonPair:
    return ComparisonPair(
        pdf_label=pdf_label,
        pdf_original=pdf.original if pdf else None,
        pdf_value=pdf.value if pdf else None,
        pdf_page=pdf.page if pdf else None,
        google_label=google_label,
        google_value=google_value,
        google_label_status=google_label_status,
        outcome=outcome,
        reason=reason,
        google_source="google_finance",
        pdf_source="official_pdf",
        duration_google=duration_google,
        duration_pdf=duration_pdf,
    )


# Published Maaden 2025 FS originals (BUILD D6). Not live Google integers.
_PDF_ORIGINALS: tuple[tuple[str, str, int], ...] = (
    ("Revenue", "38,577,730,228", 13),
    ("Profit for the year", "8,527,980,356", 13),
    ("Ordinary shareholders of the parent company", "7,347,878,280", 13),
    ("Basic and diluted earnings per share", "1.91", 13),
    ("Total assets", "119,757,152,175", 15),
    ("Total equity", "67,814,366,490", 15),
    ("Total liabilities", "51,942,785,685", 15),
    ("Net cash generated from operating activities", "10,927,067,206", 17),
    ("Net cash utilized in investing activities", "10,120,345,838", 18),
    ("Net cash utilized in financing activities", "5,438,421,256", 18),
    ("Cash and cash equivalents", "10,583,548,481", 15),
    ("share capital shares", "3,888,763,418", 19),
)


def fixture_pdf_facts() -> tuple[PdfFact, ...]:
    """Published FS originals as comparison facts. Not live Google payloads."""
    facts: list[PdfFact] = []
    for label, original, page in _PDF_ORIGINALS:
        value = parse_number(original)
        if label.startswith("Net cash utilized") and value is not None:
            value = -abs(value)
        facts.append(PdfFact(label, original, value, page, "annual"))
    return tuple(facts)


def facts_from_document(doc: ExtractedDocument) -> tuple[PdfFact, ...]:
    facts: list[PdfFact] = []
    for label, original, page in _PDF_ORIGINALS:
        needle = original.strip("()")
        label_query = "share capital" if label == "share capital shares" else label
        hit = find_line_item(doc, label_query)
        search = search_extracted(doc, needle)
        original_hit = next((h for h in search.hits if h.page_number == page), search.hits[0] if search.hits else None)
        value = parse_number(original)
        if label.startswith("Net cash utilized") and value is not None:
            value = -abs(value)
        page_no = page
        if original_hit is not None:
            page_no = original_hit.page_number
        elif hit.status == "found" and hit.page_number:
            page_no = hit.page_number
        if search.status != "found" and hit.status != "found":
            facts.append(PdfFact(label, original, None, page, "annual"))
            continue
        facts.append(PdfFact(label, original, value, page_no, "annual"))
    return tuple(facts)


def compare_statements(
    *,
    income: FinancialsResult,
    balance: FinancialsResult,
    cash_flow: FinancialsResult,
    pdf_facts: Sequence[PdfFact],
    google_frequency: str,
) -> tuple[ComparisonPair, ...]:
    facts = {f.label: f for f in pdf_facts}
    inc = _period_2025(income)
    bs = _period_2025(balance)
    cf = _period_2025(cash_flow)
    duration = google_frequency if income.statement == "income_statement" else None
    if google_frequency == "quarterly":
        duration = "quarterly"

    def annual_or_not(pdf_label: str, **kwargs) -> ComparisonPair:
        pdf = facts.get(pdf_label)
        if google_frequency == "quarterly":
            return _pair(
                pdf=pdf,
                pdf_label=pdf_label,
                google_label=kwargs.get("google_label"),
                google_value=kwargs.get("google_value"),
                google_label_status=kwargs.get("google_label_status", "display_verified"),
                outcome="not_comparable",
                reason="Google quarterly cell cannot be compared to an annual PDF line without an explicit duration mismatch.",
                duration_google="quarterly",
            )
        return _pair(pdf=pdf, pdf_label=pdf_label, duration_google=kwargs.get("duration_google", "annual"), **kwargs)

    pairs: list[ComparisonPair] = []

    revenue_row = _labeled_row(inc, "Revenue")
    pdf_rev = facts.get("Revenue")
    if google_frequency == "quarterly":
        pairs.append(
            annual_or_not(
                "Revenue",
                google_label="Revenue",
                google_value=revenue_row.value if revenue_row else None,
                google_label_status="display_verified",
            )
        )
        # Remaining pairs also not_comparable — still emit the required set.
        for label in (
            "Profit for the year",
            "Ordinary shareholders of the parent company",
            "Basic and diluted earnings per share",
            "Total assets",
            "Total equity",
            "Total liabilities",
            "Net cash generated from operating activities",
            "Net cash utilized in investing activities",
            "Net cash utilized in financing activities",
            "Cash and cash equivalents",
            "share capital shares",
        ):
            pairs.append(
                annual_or_not(
                    label,
                    google_label=None,
                    google_value=None,
                    google_label_status="unverified",
                )
            )
        return tuple(pairs)

    pairs.append(
        _pair(
            pdf=pdf_rev,
            pdf_label="Revenue",
            google_label="Revenue",
            google_value=revenue_row.value if revenue_row else None,
            google_label_status="display_verified",
            outcome="match" if revenue_row and pdf_rev and _close(revenue_row.value, pdf_rev.value) else "unavailable",
            reason="Google annual Income statement Revenue vs PDF Revenue; same period-end; full SAR.",
            duration_google="annual",
        )
    )

    ni = _labeled_row(inc, "Net income")
    profit = facts.get("Profit for the year")
    pairs.append(
        _pair(
            pdf=profit,
            pdf_label="Profit for the year",
            google_label="Net income",
            google_value=ni.value if ni else None,
            google_label_status="display_verified",
            outcome="mismatch",
            reason="Google Net income is not PDF Profit for the year (labels kept separate; NCI can differ).",
            duration_google="annual",
        )
    )
    parent = facts.get("Ordinary shareholders of the parent company")
    pairs.append(
        _pair(
            pdf=parent,
            pdf_label="Ordinary shareholders of the parent company",
            google_label="Net income",
            google_value=ni.value if ni else None,
            google_label_status="display_verified",
            outcome="match" if ni and parent and _close(ni.value, parent.value) else "mismatch",
            reason="Google Net income compared to PDF attributable-to-parent, not to Profit for the year.",
            duration_google="annual",
        )
    )

    eps_row = _labeled_row(inc, "Earnings per share")
    pdf_eps = facts.get("Basic and diluted earnings per share")
    pairs.append(
        _pair(
            pdf=pdf_eps,
            pdf_label="Basic and diluted earnings per share",
            google_label="Earnings per share",
            google_value=eps_row.value if eps_row else None,
            google_label_status="display_verified",
            outcome="match" if eps_row and pdf_eps and _close(eps_row.value, pdf_eps.value) else "unavailable",
            reason="Google annual EPS vs PDF basic and diluted EPS.",
            duration_google="annual",
        )
    )

    def unverified_numeric(pdf_label: str, period: StatementPeriod | None, duration: str) -> ComparisonPair:
        pdf = facts.get(pdf_label)
        row = _unverified_with_value(period, pdf.value if pdf else None)
        if row is None or pdf is None or pdf.value is None:
            return _pair(
                pdf=pdf,
                pdf_label=pdf_label,
                google_label=None,
                google_value=None,
                google_label_status="unverified",
                outcome="unavailable",
                reason="No display-verified Google label; PDF integer not found in unverified vector.",
                duration_google=duration,
            )
        return _pair(
            pdf=pdf,
            pdf_label=pdf_label,
            google_label=None,
            google_value=row.value,
            google_label_status="unverified",
            outcome="match",
            reason="Numeric agreement on an unverified Google slot vs PDF label; Google display label is not claimed.",
            duration_google=duration,
        )

    pairs.append(unverified_numeric("Total assets", bs, "point_in_time"))
    pairs.append(unverified_numeric("Total equity", bs, "point_in_time"))
    pairs.append(unverified_numeric("Total liabilities", bs, "point_in_time"))
    pairs.append(unverified_numeric("Net cash generated from operating activities", cf, "period"))
    pairs.append(unverified_numeric("Net cash utilized in investing activities", cf, "period"))
    pairs.append(unverified_numeric("Net cash utilized in financing activities", cf, "period"))

    cash_pdf = facts.get("Cash and cash equivalents")
    auto = _unverified_with_value(bs, cash_pdf.value if cash_pdf else None)
    pairs.append(
        _pair(
            pdf=cash_pdf,
            pdf_label="Cash and cash equivalents",
            google_label=None,
            google_value=None if auto is None else auto.value,
            google_label_status="unverified",
            outcome="mismatch",
            reason="Google cash line is not display-verified; PDF cash is not auto-identified with an unverified Google slot (different definition).",
            duration_google="point_in_time",
        )
    )
    shares_pdf = facts.get("share capital shares")
    pairs.append(
        _pair(
            pdf=shares_pdf,
            pdf_label="share capital shares",
            google_label=None,
            google_value=None,
            google_label_status="unverified",
            outcome="mismatch",
            reason="Google shares-outstanding-like slot is not the PDF issued share capital count.",
            duration_google="point_in_time",
        )
    )
    return tuple(pairs)


def extract_pdf_facts(path: Path, storage_root: Path) -> tuple[ExtractedDocument, tuple[PdfFact, ...]]:
    doc = extract_report(path, storage_root=storage_root, pages=(13, 15, 17, 18, 19))
    return doc, facts_from_document(doc)
