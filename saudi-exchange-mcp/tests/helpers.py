"""Helpers for synthetic PDFs and fake HTTP — no live payloads."""

from __future__ import annotations

from dataclasses import dataclass, field


def synthetic_pdf_bytes(page_text: str) -> bytes:
    """Minimal %PDF with a single page containing latin-1 text."""
    escaped = page_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n",
        b"4 0 obj<</Length %d>>stream\n" % len(stream) + stream + b"\nendstream\nendobj\n",
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n",
    ]
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body = header
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body += obj
    xref_pos = len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("ascii")
    trailer = (
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n"
        + str(xref_pos).encode("ascii")
        + b"\n%%EOF\n"
    )
    return body + xref + trailer


@dataclass
class FakeResponse:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)
    url: str = ""
    error: str | None = None


class FakeTransport:
    """Scripted HTTP for tests. Does not touch the network."""

    def __init__(self, routes: dict[str, FakeResponse | list[FakeResponse]]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        max_bytes: int | None = None,
    ) -> FakeResponse:
        del headers, timeout
        self.calls.append((method, url))
        entry = self.routes.get(url)
        if entry is None:
            return FakeResponse(status=404, body=b"not found", url=url)
        if isinstance(entry, list):
            if not entry:
                return FakeResponse(status=500, body=b"exhausted", url=url)
            resp = entry.pop(0)
        else:
            resp = entry
        body = resp.body
        if max_bytes is not None:
            body = body[:max_bytes]
        return FakeResponse(
            status=resp.status,
            body=body,
            headers=dict(resp.headers),
            url=resp.url or url,
            error=resp.error,
        )
