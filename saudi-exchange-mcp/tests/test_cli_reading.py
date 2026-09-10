"""D7: CLI extract / read / search with page and hash provenance."""

from __future__ import annotations

import json
from pathlib import Path

from pdf_fixtures import text_pdf

from saudi_exchange_reports.cli import main


def _put(tmp_path: Path, name: str, data: bytes) -> Path:
    storage = tmp_path / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / name
    path.write_bytes(data)
    return path


def test_cli_extract_read_search(tmp_path: Path, capsys):
    pdf = _put(tmp_path, "cli.pdf", text_pdf(["Share capital SAR 10", "Notes body without the figure"]))
    storage = str(tmp_path / "reports")
    rc = main(["extract", "--path", str(pdf), "--storage", storage])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["status"] == "ok"
    assert payload["content_hash"]
    assert payload["pages"][0]["page_number"] == 1
    assert payload["pages"][0]["method"] == "native"
    assert "Share capital SAR 10" in payload["pages"][0]["text"]

    rc = main(["read", "--path", str(pdf), "--storage", storage, "--page", "2"])
    read_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert read_payload["pages"][0]["page_number"] == 2
    assert "Notes body" in read_payload["pages"][0]["text"]

    rc = main(["search", "--path", str(pdf), "--storage", storage, "--query", "share capital"])
    search_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert search_payload["status"] == "found"
    assert search_payload["hits"][0]["page_number"] == 1
    assert search_payload["hits"][0]["content_hash"] == payload["content_hash"]

    rc = main(["search", "--path", str(pdf), "--storage", storage, "--query", "no-such-line-item-xyz"])
    miss = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert miss["status"] == "not_found"
    assert miss["hits"] == []
    assert "zero" not in miss["reason"].lower()


def test_cli_extract_rejects_non_pdf(tmp_path: Path, capsys):
    storage = tmp_path / "reports"
    storage.mkdir()
    path = storage / "x.pdf"
    path.write_bytes(b"not-pdf")
    rc = main(["extract", "--path", str(path), "--storage", str(storage)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["status"] == "failed"
    assert payload["error_type"] == "InvalidPdf"
