"""Extract, read, and search stored report PDFs with page-level provenance."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import pdfplumber
from pypdf import PdfReader

from saudi_exchange_reports.errors import InvalidPdf, UnsafeDestination
from saudi_exchange_reports.metadata import FinancialMetadata, infer_financial_metadata
from saudi_exchange_reports.ocr import (
    DEFAULT_OCR_DPI,
    native_is_usable,
    ocr_pdf_page,
)
from saudi_exchange_reports.storage import ensure_within, resolve_storage_root

_ARABIC_RUN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
_NUMERIC = re.compile(
    r"^\(?\s*(?:SAR|SR|USD)?\s*[-−–]?\s*\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*\)?$"
    r"|^\(?\s*(?:SAR|SR|USD)?\s*[-−–]?\s*\d+(?:\.\d+)?\s*\)?$",
    re.I,
)


def logicalize_arabic(text: str) -> str:
    return _ARABIC_RUN.sub(lambda m: m.group(0)[::-1], text)


def parse_number(original: str) -> float | None:
    s = original.strip()
    if s == "" or s in {"-", "—", "–", "n/a", "N/A", "n.a.", "na"}:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = re.sub(r"^(SAR|SR|USD)\s*", "", s, flags=re.I)
    s = s.replace(",", "").replace(" ", "").replace("−", "-").replace("–", "-")
    if not s or s in {".", "-"}:
        return None
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    if neg:
        value = -value
    return value


@dataclass(frozen=True)
class ExtractedSpan:
    original: str
    parsed_number: float | None
    content_hash: str
    local_path: str
    page_number: int
    method: str
    confidence: str = "certain"


@dataclass(frozen=True)
class TableCell:
    row: int
    column: int
    original: str
    parsed_number: float | None
    status: str
    content_hash: str
    local_path: str
    page_number: int
    method: str


@dataclass(frozen=True)
class ExtractedTable:
    page_number: int
    cells: tuple[TableCell, ...]


@dataclass(frozen=True)
class PageExtraction:
    page_number: int
    method: str
    text: str
    spans: tuple[ExtractedSpan, ...]
    tables: tuple[ExtractedTable, ...]
    content_hash: str
    local_path: str
    unreadable_reason: str | None = None
    confidence_label: str | None = None
    ocr_mean_confidence: float | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    content_hash: str
    local_path: Path
    pages: tuple[PageExtraction, ...]
    metadata: FinancialMetadata

    def to_dict(self) -> dict:
        payload = {
            "content_hash": self.content_hash,
            "local_path": str(self.local_path),
            "pages": [_page_dict(p) for p in self.pages],
            "metadata": _metadata_dict(self.metadata),
        }
        return payload


@dataclass(frozen=True)
class SearchHit:
    original: str
    page_number: int
    content_hash: str
    method: str


@dataclass(frozen=True)
class SearchResult:
    status: str
    query: str
    hits: tuple[SearchHit, ...]
    reason: str


@dataclass(frozen=True)
class LineItemResult:
    status: str
    original: str | None
    parsed_number: float | None
    page_number: int | None
    content_hash: str | None
    reason: str


def resolve_readable_pdf(
    path: Path,
    *,
    storage_root: Path,
    extra_allowed_roots: Sequence[Path] = (),
) -> Path:
    root = resolve_storage_root(storage_root)
    dest = path.expanduser().resolve()
    allowed = [root, *[resolve_storage_root(Path(p)) for p in extra_allowed_roots]]
    inside = False
    for allowed_root in allowed:
        try:
            dest.relative_to(allowed_root)
            inside = True
            break
        except ValueError:
            continue
    if not inside:
        raise UnsafeDestination(f"{dest} is outside {root}")
    if not dest.is_file():
        raise InvalidPdf(f"{dest} is not a file")
    data = dest.read_bytes()
    if not data.startswith(b"%PDF"):
        raise InvalidPdf(f"{dest} is not a PDF")
    return dest


def extract_report(
    path: Path,
    *,
    storage_root: Path,
    extra_allowed_roots: Sequence[Path] = (),
    pages: Sequence[int] | None = None,
    persist: bool = True,
    ocr_dpi: int = DEFAULT_OCR_DPI,
) -> ExtractedDocument:
    pdf_path = resolve_readable_pdf(
        path, storage_root=storage_root, extra_allowed_roots=extra_allowed_roots
    )
    data = pdf_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    page_list = tuple(pages) if pages is not None else None
    if persist:
        cached = _load_cache(storage_root, digest, page_list)
        if cached is not None:
            return cached
    reader = PdfReader(str(pdf_path), strict=False)
    total = len(reader.pages)
    wanted = list(page_list) if page_list is not None else list(range(1, total + 1))
    for number in wanted:
        if number < 1 or number > total:
            raise InvalidPdf(f"Page {number} is outside 1..{total}")
    extracted_pages: list[PageExtraction] = []
    for number in wanted:
        extracted_pages.append(
            _extract_one_page(
                pdf_path,
                reader,
                page_number=number,
                digest=digest,
                ocr_dpi=ocr_dpi,
            )
        )
    metadata = infer_financial_metadata([(p.page_number, p.text) for p in extracted_pages])
    doc = ExtractedDocument(
        content_hash=digest,
        local_path=pdf_path,
        pages=tuple(extracted_pages),
        metadata=metadata,
    )
    if persist:
        _save_cache(storage_root, doc, page_list)
    return doc


def read_pages(doc: ExtractedDocument, start: int, end: int | None = None) -> tuple[PageExtraction, ...]:
    last = start if end is None else end
    if last < start:
        raise ValueError("end must be >= start")
    selected = tuple(p for p in doc.pages if start <= p.page_number <= last)
    return selected


def search_extracted(doc: ExtractedDocument, query: str) -> SearchResult:
    needle = query.strip()
    if not needle:
        return SearchResult(
            status="not_found",
            query=query,
            hits=(),
            reason="Empty query is not_found; this is not a numeric amount and is not proof that an activity did not occur.",
        )
    variants = {needle, logicalize_arabic(needle)}
    hits: list[SearchHit] = []
    for page in doc.pages:
        if page.method == "unreadable":
            continue
        for span in page.spans or _spans_from_text(
            page.text, digest=doc.content_hash, path=str(doc.local_path), page_number=page.page_number, method=page.method
        ):
            hay = span.original + "\n" + logicalize_arabic(span.original)
            if any(_contains(hay, v) for v in variants):
                hits.append(
                    SearchHit(
                        original=span.original,
                        page_number=page.page_number,
                        content_hash=doc.content_hash,
                        method=page.method,
                    )
                )
    if hits:
        return SearchResult(status="found", query=query, hits=tuple(hits), reason="Matched extracted spans.")
    return SearchResult(
        status="not_found",
        query=query,
        hits=(),
        reason=(
            "No extracted span matched the query (not_found). An empty hit list is not a numeric amount "
            "and is not proof that the activity did not occur."
        ),
    )


def find_line_item(doc: ExtractedDocument, label: str) -> LineItemResult:
    needle = label.strip()
    if not needle:
        return LineItemResult(
            status="not_found",
            original=None,
            parsed_number=None,
            page_number=None,
            content_hash=None,
            reason="Empty label is not_found, not zero.",
        )
    variants = {needle, logicalize_arabic(needle)}
    for page in doc.pages:
        for line in page.text.splitlines():
            hay = line + "\n" + logicalize_arabic(line)
            if any(_contains(hay, v) for v in variants):
                parsed = _first_number_in(line)
                return LineItemResult(
                    status="found",
                    original=line.strip(),
                    parsed_number=parsed,
                    page_number=page.page_number,
                    content_hash=doc.content_hash,
                    reason="Matched an extracted line.",
                )
    return LineItemResult(
        status="not_found",
        original=None,
        parsed_number=None,
        page_number=None,
        content_hash=doc.content_hash,
        reason=(
            f"Line item {label!r} was not found on the cited pages. "
            "Missing is not zero and is not proof that the activity did not occur."
        ),
    )


def parse_page_spec(spec: str) -> tuple[int, ...]:
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return tuple(pages)


def _contains(haystack: str, needle: str) -> bool:
    return needle.casefold() in haystack.casefold()


def _first_number_in(text: str) -> float | None:
    for token in re.split(r"\s+", text):
        parsed = parse_number(token)
        if parsed is not None:
            return parsed
    return None


def _spans_from_text(
    text: str,
    *,
    digest: str,
    path: str,
    page_number: int,
    method: str,
    confidence: str = "certain",
) -> tuple[ExtractedSpan, ...]:
    spans: list[ExtractedSpan] = []
    for line in text.splitlines():
        original = line.strip()
        if not original:
            continue
        spans.append(
            ExtractedSpan(
                original=original,
                parsed_number=parse_number(original) if _NUMERIC.match(original) else _first_number_in(original),
                content_hash=digest,
                local_path=path,
                page_number=page_number,
                method=method,
                confidence=confidence,
            )
        )
    return tuple(spans)


def _extract_tables(
    path: Path,
    page_number: int,
    *,
    digest: str,
    method: str,
) -> tuple[ExtractedTable, ...]:
    try:
        with pdfplumber.open(str(path)) as pdf:
            plumber_page = pdf.pages[page_number - 1]
            raw_tables = plumber_page.extract_tables() or []
    except Exception:
        return ()
    tables: list[ExtractedTable] = []
    for raw in raw_tables:
        cells: list[TableCell] = []
        for r_i, row in enumerate(raw):
            for c_i, value in enumerate(row):
                if value is None:
                    original = ""
                    status = "unavailable"
                    parsed = None
                else:
                    original = value.strip() if isinstance(value, str) else str(value)
                    if original == "":
                        status = "blank"
                        parsed = None
                    else:
                        status = "present"
                        parsed = parse_number(original)
                cells.append(
                    TableCell(
                        row=r_i,
                        column=c_i,
                        original=original,
                        parsed_number=parsed,
                        status=status,
                        content_hash=digest,
                        local_path=str(path),
                        page_number=page_number,
                        method=method,
                    )
                )
        if cells:
            tables.append(ExtractedTable(page_number=page_number, cells=tuple(cells)))
    return tuple(tables)


def _extract_one_page(
    path: Path,
    reader: PdfReader,
    *,
    page_number: int,
    digest: str,
    ocr_dpi: int,
) -> PageExtraction:
    local_path = str(path)
    pdf_page = reader.pages[page_number - 1]
    try:
        native = pdf_page.extract_text() or ""
    except Exception:
        native = ""
    if native_is_usable(native):
        method = "native"
        text = native
        tables = _extract_tables(path, page_number, digest=digest, method=method)
        spans = _spans_from_text(text, digest=digest, path=local_path, page_number=page_number, method=method)
        return PageExtraction(
            page_number=page_number,
            method=method,
            text=text,
            spans=spans,
            tables=tables,
            content_hash=digest,
            local_path=local_path,
            unreadable_reason=None,
            confidence_label="certain",
        )
    ocr = ocr_pdf_page(path, page_number, dpi=ocr_dpi)
    native_stripped = native.strip()
    if ocr.unreadable_reason and letter_count_safe(ocr.text) < 8:
        method = "unreadable"
        text = ocr.text
        return PageExtraction(
            page_number=page_number,
            method=method,
            text=text,
            spans=(),
            tables=(),
            content_hash=digest,
            local_path=local_path,
            unreadable_reason=ocr.unreadable_reason,
            confidence_label="unavailable",
            ocr_mean_confidence=ocr.mean_confidence,
        )
    if native_stripped and ocr.text.strip():
        method = "mixed"
        text = native.rstrip() + "\n" + ocr.text
    else:
        method = "ocr"
        text = ocr.text
    confidence = ocr.confidence_label if ocr.confidence_label in {"certain", "uncertain"} else "uncertain"
    tables = _extract_tables(path, page_number, digest=digest, method=method)
    spans = _spans_from_text(
        text, digest=digest, path=local_path, page_number=page_number, method=method, confidence=confidence
    )
    return PageExtraction(
        page_number=page_number,
        method=method,
        text=text,
        spans=spans,
        tables=tables,
        content_hash=digest,
        local_path=local_path,
        unreadable_reason=None,
        confidence_label=confidence,
        ocr_mean_confidence=ocr.mean_confidence,
    )


def letter_count_safe(text: str) -> int:
    return sum(1 for ch in text if ch.isalpha())


def _page_dict(page: PageExtraction) -> dict:
    return {
        "page_number": page.page_number,
        "method": page.method,
        "text": page.text,
        "unreadable_reason": page.unreadable_reason,
        "confidence_label": page.confidence_label,
        "content_hash": page.content_hash,
        "local_path": page.local_path,
        "spans": [asdict(s) for s in page.spans],
        "tables": [
            {
                "page_number": table.page_number,
                "cells": [asdict(c) for c in table.cells],
            }
            for table in page.tables
        ],
    }


def _metadata_dict(meta: FinancialMetadata) -> dict:
    return {
        name: asdict(getattr(meta, name))
        for name in (
            "currency",
            "scale",
            "period",
            "duration",
            "quarterly_vs_cumulative",
            "scope",
            "restatement",
        )
    }


def _cache_path(storage_root: Path, digest: str, pages: tuple[int, ...] | None) -> Path:
    root = resolve_storage_root(storage_root)
    folder = ensure_within(root, root / "_extracted")
    key = digest if pages is None else f"{digest}-p{'-'.join(str(p) for p in pages)}"
    return ensure_within(root, folder / f"{key}.json")


def _save_cache(storage_root: Path, doc: ExtractedDocument, pages: tuple[int, ...] | None) -> None:
    path = _cache_path(storage_root, doc.content_hash, pages)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_cache(
    storage_root: Path, digest: str, pages: tuple[int, ...] | None
) -> ExtractedDocument | None:
    path = _cache_path(storage_root, digest, pages)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if payload.get("content_hash") != digest:
        return None
    return _document_from_dict(payload)


def _document_from_dict(payload: dict) -> ExtractedDocument:
    from saudi_exchange_reports.metadata import MetadataField

    def field(raw: dict) -> MetadataField:
        return MetadataField(
            status=raw.get("status", "unknown"),
            value=raw.get("value"),
            evidence=raw.get("evidence"),
            page_number=raw.get("page_number"),
        )

    meta_raw = payload.get("metadata") or {}
    metadata = FinancialMetadata(
        currency=field(meta_raw.get("currency") or {}),
        scale=field(meta_raw.get("scale") or {}),
        period=field(meta_raw.get("period") or {}),
        duration=field(meta_raw.get("duration") or {}),
        quarterly_vs_cumulative=field(meta_raw.get("quarterly_vs_cumulative") or {}),
        scope=field(meta_raw.get("scope") or {}),
        restatement=field(meta_raw.get("restatement") or {}),
    )
    pages: list[PageExtraction] = []
    for raw in payload.get("pages") or []:
        spans = tuple(
            ExtractedSpan(
                original=s["original"],
                parsed_number=s.get("parsed_number"),
                content_hash=s["content_hash"],
                local_path=s["local_path"],
                page_number=s["page_number"],
                method=s["method"],
                confidence=s.get("confidence", "certain"),
            )
            for s in raw.get("spans") or []
        )
        tables = tuple(
            ExtractedTable(
                page_number=t["page_number"],
                cells=tuple(
                    TableCell(
                        row=c["row"],
                        column=c["column"],
                        original=c["original"],
                        parsed_number=c.get("parsed_number"),
                        status=c["status"],
                        content_hash=c["content_hash"],
                        local_path=c["local_path"],
                        page_number=c["page_number"],
                        method=c["method"],
                    )
                    for c in t.get("cells") or []
                ),
            )
            for t in raw.get("tables") or []
        )
        pages.append(
            PageExtraction(
                page_number=raw["page_number"],
                method=raw["method"],
                text=raw.get("text") or "",
                spans=spans,
                tables=tables,
                content_hash=payload["content_hash"],
                local_path=payload["local_path"],
                unreadable_reason=raw.get("unreadable_reason"),
                confidence_label=raw.get("confidence_label"),
                ocr_mean_confidence=raw.get("ocr_mean_confidence"),
            )
        )
    return ExtractedDocument(
        content_hash=payload["content_hash"],
        local_path=Path(payload["local_path"]),
        pages=tuple(pages),
        metadata=metadata,
    )
