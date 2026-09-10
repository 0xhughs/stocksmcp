# Saudi Exchange reports (Hybrid Pilot v0)

Python 3.12 library and **local stdio MCP server** for **pilot** Main Market company identity, report listing, original-PDF retrieval, page-level reading/search, and a **Google Finance** overview/news/profile/earnings/financials client for the same identities. Google Finance reuse is local, personal, and user-initiated; it does not license Google or exchange data. Google tables are not audited Saudi Exchange filings.

The product MCP process is `python -m saudi_exchange_reports.mcp` (console script `saudi-exchange-mcp`). It is **not** `python -m google_finance_mcp` / `google_finance_mcp.server`. Installing or enabling the server does not run research until the host calls tools.

Install (local venv):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Live listing fallback uses system Chrome via Playwright (optional extra):
# .venv/bin/pip install 'playwright>=1.40'
# OCR (slice 02) needs local Tesseract plus English/Arabic data:
# sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara poppler-utils
```

Tests (no live Saudi Exchange website and **no live Google**). Synthetic PDFs, HTML fixtures, and hand-written Google dataset fixtures. Stored Maaden FS checks run when the gitignored PDF is present. Live Google Finance checks are skipped unless you pass `--live-google` or set `SAUDI_LIVE_GOOGLE=1`:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
# opt-in live Aramco Google checks (bodies stay gitignored):
# SAUDI_LIVE_GOOGLE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/ -m live_google -q
# opt-in live stdio MCP session (same flag; also --live-mcp):
# SAUDI_LIVE_GOOGLE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/test_mcp_live.py -q
```

CLI (slice 01 retrieval):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports resolve --ticker 2222
PYTHONPATH=src python3 -m saudi_exchange_reports retrieve \
  --ticker 1211 --period 2025 --type annual --language en \
  --storage storage/reports
PYTHONPATH=src python3 -m saudi_exchange_reports retrieve-url \
  --ticker 1211 \
  --url 'https://www.saudiexchange.sa/Resources/fsPdf/<issuer>_…_En.pdf' \
  --period 2025 --type annual --language en \
  --storage storage/reports
```

CLI (slice 02 reading). `--path` must be inside `--storage` (or a test fixture root). Page numbers are 1-based PDF indices:

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports extract \
  --path storage/reports/1211/<sha256>.pdf \
  --storage storage/reports \
  --pages 13-18,19
PYTHONPATH=src python3 -m saudi_exchange_reports read \
  --path storage/reports/1211/<sha256>.pdf \
  --storage storage/reports --pages 13-18,19 --page 13
PYTHONPATH=src python3 -m saudi_exchange_reports search \
  --path storage/reports/1211/<sha256>.pdf \
  --storage storage/reports --pages 13-18,19 \
  --query 'share capital'
```

CLI (slices 03–04 Google Finance). Commands resolve the **existing** shared identity, then call Google Finance. Do not treat returned quotes, news, profile text, earnings, or financial tables as licensed data or as audited filings; do not commit live payloads. Do not copy live prices, headlines, or Google JSON into docs:

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports resolve ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-overview ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-news ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-profile ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-inventory ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-earnings ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-financials ARAMCO --statement income --frequency quarterly
PYTHONPATH=src python3 -m saudi_exchange_reports google-coverage ARAMCO
PYTHONPATH=src python3 -m saudi_exchange_reports google-crosscheck MAADEN --facts fixture
# optional stored-PDF comparison (gitignored Maaden FS):
# PYTHONPATH=src python3 -m saudi_exchange_reports google-crosscheck MAADEN \
#   --pdf storage/reports/1211/<sha256>.pdf --storage storage/reports
```

Native text is used when a page has text operators. Image-only pages are rasterized and OCR’d with local Tesseract (`eng+ara`). Pages that remain unreadable are flagged, not omitted. Extraction JSON is cached under `storage/reports/_extracted/` (gitignored). Do not commit PDFs or full extraction dumps.

`retrieve` always re-fetches the company profile (a cached listing is not proof that no newer report exists). If urllib `statementsTabData` returns HTTP 500, `retrieve` falls back to **browser-driven** Financial Statements tab HTML on `www.saudiexchange.sa` (Playwright + Chrome; not an official API) and then downloads the selected `/Resources/fsPdf/` object with urllib. Use `--no-browser` to skip that fallback. `retrieve-url` still requires a known host URL and does not invent filenames.

Default storage is `storage/reports/` (gitignored). Provenance is written next to each PDF as `{sha256}.pdf.json`. Optional live Google dumps go only under `evidence/live-payloads/` (gitignored).

## Cursor MCP install (stdio, local, not a deployment)

Copy-paste example: `evidence/05-hybrid-mcp/cursor-mcp.json.example`. Put the same object in the project file `.cursor/mcp.json` and/or the user file `~/.cursor/mcp.json`. This is a **local, personal, user-initiated** stdio server. It is not a hosted/multi-user service, not Cursor Marketplace publishing, and not Streamable HTTP/SSE remote deployment.

```json
{
  "mcpServers": {
    "saudi-exchange": {
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "saudi_exchange_reports.mcp"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "SAUDI_REPORTS_STORAGE": "${workspaceFolder}/storage/reports"
      }
    }
  }
}
```

`${workspaceFolder}` interpolation is allowed. Point `command` at this workspace's venv. Optional: `SAUDI_MCP_USE_BROWSER=1` enables the existing Playwright tab fallback for Saudi listing (same as slice 01). Live Google HTTP happens only when a Google tool is called.

MCP session evidence (fixture vs live vs stored-PDF): `evidence/05-hybrid-mcp/`.

Access notes and PDF hashes: `evidence/01-report-retrieval/`. Reading evidence: `evidence/02-report-reading/`. Google Finance notices, mappings, inventory, and checks: `evidence/03-google-overview/`. Earnings/financials coverage and PDF cross-checks: `evidence/04-google-financials/`. The Saudi Exchange site is not a documented public reports API. From some networks, `urllib` with `Accept: */*` succeeds while `curl` receives Akamai 403.
