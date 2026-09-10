# Checks

Routine tests **do not** require the live website. They use `tests/fixtures/` and synthetic `%PDF` bytes. Browser listing is injected as a fake tab renderer in unit tests.

## Command

From `/workspace/saudi-exchange-mcp`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

Equivalent: `PYTHONPATH=src python3 -m pytest tests/ -q` after installing `pytest`, `pypdf`, and `playwright` (Playwright is not launched by routine tests).

Builder repair result (2026-09-09, disp-01-impl-002): **57 passed**.

## What the tests prove

| Criterion | Tests | Live? |
|---|---|---|
| D2 identity: Arabic/English/ticker, ambiguous, conflicting, unknown, not-found, wrong-exchange; distinct Saudi vs unverified Google slot | `tests/test_identity.py` | No |
| D3 list/select annual vs interim vs other; languages; missing publication date; unavailable period; ambiguous language | `tests/test_listing.py`, fixture `tests/fixtures/maaden_reports.html` | No |
| D3 live matrix (year columns, empty SVG link text, Q3 period, Arabic labels after an English ESG section) | `tests/test_listing.py`, `tests/fixtures/maaden_live_matrix.html` | Shape from live HTML; URLs are source-observed |
| D3 statements-tab URL derived from untrusted HTML; off-host/javascript ignored | `tests/test_listing.py` | No |
| D3 live-shaped client: profile without `fsPdf` then tab HTML; HTTP 500 is unavailable (not an empty market); browser-tab HTML used after 500; off-host profile rejected | `tests/test_client.py` | No |
| D4 download, `%PDF` magic, provenance sidecar, page inspection | `tests/test_retrieval.py` | Additional live proof in `live-retrieval.md` |
| D5 cache reuse; changed bytes keep prior file; corrupt cache redownload; listing `from_cache` is labelled | `tests/test_retrieval.py`, `tests/test_untrusted.py`, `tests/test_client.py` | Live cache_hit recorded for the earlier retrieve-url object |
| D6 HTML-as-PDF, failed/partial download, 403, unsafe destination, disallowed redirect, 5xx retry, no retry on 403, untrusted links | `tests/test_failures.py`, `tests/test_untrusted.py` | Live 403 without `Accept` documented in `access.md` |

## Live extras (not required for `pytest`)

See `live-retrieval.md` and `live-listing.json`. Reviewer should treat:

- **Verified live:** Maaden browser-driven Financial Statements table with `/Resources/fsPdf/` rows; `retrieve --ticker 1211 --period 2025 --type annual --language en` selected `370_0_2026-03-11_15-58-59_En.pdf` from that table and stored original bytes (hash `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`).
- **Verified live failure (urllib hop):** `statementsTabData` HTTP 500; not treated as an empty market.
- **Verified live listing only:** Aramco `2222` also returned 44 fsPdf rows; PDF not downloaded.
- **Unverified live:** Aramco PDF download; live restatement of a stored file.
- **Untested by design:** Google Finance identifier verification (slice 03).
