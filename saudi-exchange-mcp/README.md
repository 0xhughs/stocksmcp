# Saudi Exchange reports (slice 01)

Python 3.12 library for **pilot** Main Market company identity, report listing, and original-PDF retrieval. This is **not** an MCP server and **not** a Google Finance client.

Install (local venv):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Live listing fallback uses system Chrome via Playwright (optional extra):
# .venv/bin/pip install 'playwright>=1.40'

```

Tests (no live website):

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

CLI:

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

`retrieve` always re-fetches the company profile (a cached listing is not proof that no newer report exists). If urllib `statementsTabData` returns HTTP 500, `retrieve` falls back to **browser-driven** Financial Statements tab HTML on `www.saudiexchange.sa` (Playwright + Chrome; not an official API) and then downloads the selected `/Resources/fsPdf/` object with urllib. Use `--no-browser` to skip that fallback. `retrieve-url` still requires a known host URL and does not invent filenames.

Default storage is `storage/reports/` (gitignored). Provenance is written next to each PDF as `{sha256}.pdf.json`.

Access notes, the live listing dump, and PDF hashes: `evidence/01-report-retrieval/`. The site is not a documented public reports API. From some networks, `urllib` with `Accept: */*` succeeds while `curl` receives Akamai 403.
