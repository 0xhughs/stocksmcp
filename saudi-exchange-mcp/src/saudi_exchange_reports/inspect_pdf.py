"""Inspect enough of a PDF page to confirm company identity and period."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from saudi_exchange_reports.models import CompanyIdentity


@dataclass(frozen=True)
class PdfInspection:
    identity_confirmed: bool
    period_confirmed: bool
    page_text: str
    page_count: int | None
    reason: str


def _needles_for(company: CompanyIdentity) -> tuple[str, ...]:
    values = [
        company.english_name,
        company.arabic_name,
        company.ticker,
        *company.aliases,
    ]
    return tuple(v for v in values if v)


def inspect_pdf_identity(
    path: Path,
    *,
    company: CompanyIdentity,
    period: str | None = None,
) -> PdfInspection:
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        return PdfInspection(
            identity_confirmed=False,
            period_confirmed=False,
            page_text="",
            page_count=None,
            reason="File is not a PDF.",
        )
    try:
        reader = PdfReader(str(path), strict=False)
        page_count = len(reader.pages)
        parts: list[str] = []
        # Bounded page sample — not full extraction (slice 02).
        for page in reader.pages[:5]:
            parts.append(page.extract_text() or "")
        page_text = "\n".join(parts)
    except Exception as exc:  # untrusted PDF
        # Fallback: search embedded latin-1 strings (enough for fixtures / magic checks).
        page_text = data.decode("latin-1", errors="ignore")
        page_count = None
        reason_prefix = f"pypdf could not parse pages ({exc}); used raw-string fallback. "
    else:
        reason_prefix = ""
    blob = page_text.casefold()
    identity_confirmed = any(n.casefold() in blob for n in _needles_for(company) if len(n) >= 3)
    period_confirmed = bool(period) and period.casefold() in blob
    reason = reason_prefix
    if identity_confirmed and period_confirmed:
        reason += "Early-page text contains the company identity and requested period."
    elif identity_confirmed:
        reason += "Company identity found; requested period was not found in the inspected pages."
    elif period_confirmed:
        reason += "Period found; company identity was not found in the inspected pages."
    else:
        reason += "Inspected pages did not confirm identity or period."
    return PdfInspection(
        identity_confirmed=identity_confirmed,
        period_confirmed=period_confirmed,
        page_text=page_text[:4000],
        page_count=page_count,
        reason=reason.strip(),
    )
