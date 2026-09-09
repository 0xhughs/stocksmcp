"""Local Tesseract OCR for pages without usable native text."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

NATIVE_LETTER_THRESHOLD = 1
OCR_UNREADABLE_MEAN_CONF = 28.0
OCR_UNCERTAIN_MEAN_CONF = 55.0
DEFAULT_OCR_DPI = 200
OCR_LANG = "eng+ara"


@dataclass(frozen=True)
class OcrPageResult:
    text: str
    mean_confidence: float | None
    confidence_label: str
    unreadable_reason: str | None


def letter_count(text: str) -> int:
    return sum(1 for ch in text if ch.isalpha())


def native_is_usable(text: str) -> bool:
    return letter_count(text) >= NATIVE_LETTER_THRESHOLD


def classify_ocr(text: str, mean_confidence: float | None) -> OcrPageResult:
    letters = letter_count(text)
    if not text.strip() or letters < 8:
        return OcrPageResult(
            text=text,
            mean_confidence=mean_confidence,
            confidence_label="unavailable",
            unreadable_reason="OCR produced no usable text on this page.",
        )
    if mean_confidence is not None and mean_confidence < OCR_UNREADABLE_MEAN_CONF:
        return OcrPageResult(
            text=text,
            mean_confidence=mean_confidence,
            confidence_label="uncertain",
            unreadable_reason=f"OCR mean confidence {mean_confidence:.1f} is below the readable threshold.",
        )
    if mean_confidence is not None and mean_confidence < OCR_UNCERTAIN_MEAN_CONF:
        return OcrPageResult(
            text=text,
            mean_confidence=mean_confidence,
            confidence_label="uncertain",
            unreadable_reason=None,
        )
    return OcrPageResult(
        text=text,
        mean_confidence=mean_confidence,
        confidence_label="certain",
        unreadable_reason=None,
    )


def rasterize_pdf_page(path: Path, page_number: int, dpi: int = DEFAULT_OCR_DPI) -> Image.Image:
    from pdf2image import convert_from_path

    images = convert_from_path(
        str(path),
        first_page=page_number,
        last_page=page_number,
        dpi=dpi,
    )
    if not images:
        raise RuntimeError(f"pdf2image returned no raster for page {page_number}")
    return images[0]


def ocr_image(image: Image.Image, *, lang: str = OCR_LANG) -> tuple[str, float | None]:
    import pytesseract

    text = pytesseract.image_to_string(image, lang=lang) or ""
    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
    confs: list[float] = []
    for raw in data.get("conf", []):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            confs.append(value)
    mean = sum(confs) / len(confs) if confs else None
    return text, mean


def ocr_pdf_page(path: Path, page_number: int, *, dpi: int = DEFAULT_OCR_DPI, lang: str = OCR_LANG) -> OcrPageResult:
    if shutil.which("tesseract") is None:
        return OcrPageResult(
            text="",
            mean_confidence=None,
            confidence_label="unavailable",
            unreadable_reason="Tesseract is not installed on this machine.",
        )
    try:
        image = rasterize_pdf_page(path, page_number, dpi=dpi)
        text, mean = ocr_image(image, lang=lang)
    except Exception as exc:  # untrusted PDF / missing poppler
        return OcrPageResult(
            text="",
            mean_confidence=None,
            confidence_label="unavailable",
            unreadable_reason=f"Local OCR failed ({exc}).",
        )
    return classify_ocr(text, mean)
