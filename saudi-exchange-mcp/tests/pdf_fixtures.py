"""Synthetic PDFs for slice 02 reading tests. Not live filings."""

from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
NASKH = Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf")

_ARABIC_RUN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")


def logicalize_arabic(text: str) -> str:
    """Undo visual-order Arabic runs from simple PDF text operators."""
    return _ARABIC_RUN.sub(lambda m: m.group(0)[::-1], text)


def _register_naskh() -> str:
    name = "NotoNaskhArabic"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, str(NASKH)))
    return name


def text_pdf(pages: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for page_text in pages:
        y = 740
        for line in page_text.splitlines() or [""]:
            c.setFont("Helvetica", 12)
            c.drawString(72, y, line[:110])
            y -= 16
            if y < 48:
                break
        c.showPage()
    c.save()
    return buf.getvalue()


def arabic_text_pdf(pages: list[str]) -> bytes:
    font = _register_naskh()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for page_text in pages:
        y = 740
        for line in page_text.splitlines() or [""]:
            c.setFont(font, 16)
            c.drawString(72, y, line)
            y -= 22
        c.showPage()
    c.save()
    return buf.getvalue()


def table_pdf(rows: list[list[str]]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    table = Table(rows)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
            ]
        )
    )
    doc.build([table])
    return buf.getvalue()


def _render_lines_image(lines: list[str], *, font_path: Path, size: int, fill: str = "black") -> Image.Image:
    font = ImageFont.truetype(str(font_path), size)
    img = Image.new("RGB", (1400, 900), "white")
    draw = ImageDraw.Draw(img)
    y = 60
    for line in lines:
        draw.text((50, y), line, font=font, fill=fill)
        y += size + 18
    return img


def image_only_pdf(lines: list[str], *, arabic: bool = False) -> bytes:
    font_path = NASKH if arabic else DEJAVU
    img = _render_lines_image(lines, font_path=font_path, size=36 if not arabic else 40)
    ibuf = io.BytesIO()
    img.save(ibuf, format="JPEG", quality=95)
    ibuf.seek(0)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawImage(ImageReader(ibuf), 36, 280, width=540, height=360)
    c.showPage()
    c.save()
    return buf.getvalue()


def noise_image_pdf() -> bytes:
    img = Image.new("RGB", (800, 600), (18, 18, 18))
    draw = ImageDraw.Draw(img)
    for i in range(0, 800, 7):
        draw.line((i, 0, 800 - i, 600), fill=(22, 19, 24))
    ibuf = io.BytesIO()
    img.save(ibuf, format="JPEG", quality=20)
    ibuf.seek(0)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawImage(ImageReader(ibuf), 36, 200, width=540, height=400)
    c.showPage()
    c.save()
    return buf.getvalue()


def faint_text_image_pdf(line: str) -> bytes:
    img = Image.new("RGB", (900, 400), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(DEJAVU), 9)
    draw.text((20, 180), line, font=font, fill=(230, 230, 230))
    ibuf = io.BytesIO()
    img.save(ibuf, format="JPEG", quality=30)
    ibuf.seek(0)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawImage(ImageReader(ibuf), 36, 300, width=540, height=240)
    c.showPage()
    c.save()
    return buf.getvalue()


def mixed_native_and_image_pdf(*, native: str, image_lines: list[str]) -> bytes:
    img = _render_lines_image(image_lines, font_path=DEJAVU, size=32)
    ibuf = io.BytesIO()
    img.save(ibuf, format="JPEG", quality=95)
    ibuf.seek(0)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)
    c.drawString(72, 780, native)
    c.drawImage(ImageReader(ibuf), 36, 200, width=540, height=360)
    c.showPage()
    c.save()
    return buf.getvalue()
