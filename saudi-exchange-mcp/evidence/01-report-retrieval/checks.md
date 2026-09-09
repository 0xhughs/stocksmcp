# Checks

Routine tests **do not** require the live website. They use `tests/fixtures/` and synthetic `%PDF` bytes.

## Command

From `/workspace/saudi-exchange-mcp`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

Equivalent: `PYTHONPATH=src python3 -m pytest tests/ -q` after installing `pytest` and `pypdf`.

Builder result (2026-09-09): **50 passed**.

## What the tests prove

| Criterion | Tests | Live? |
|---|---|---|
| D2 identity: Arabic/English/ticker, ambiguous, conflicting, unknown, not-found, wrong-exchange; distinct Saudi vs unverified Google slot | `tests/test_identity.py` | No |
| D3 list/select annual vs interim vs other; languages; missing publication date; unavailable period; ambiguous language | `tests/test_listing.py`, fixture `tests/fixtures/maaden_reports.html` | No |
| D3 statements-tab URL derived from untrusted HTML; off-host/javascript ignored | `tests/test_listing.py` | No |
| D3 live-shaped client: profile without `fsPdf` then tab HTML; HTTP 500 is unavailable (not an empty market) | `tests/test_client.py` | No |
| D4 download, `%PDF` magic, provenance sidecar, page inspection | `tests/test_retrieval.py` | Additional live proof in `live-retrieval.md` |
| D5 cache reuse; changed bytes keep prior file; corrupt cache redownload; listing `from_cache` is labelled | `tests/test_retrieval.py`, `tests/test_untrusted.py`, `tests/test_client.py` | Live cache_hit recorded; no live restatement observed |
| D6 HTML-as-PDF, failed/partial download, 403, unsafe destination, disallowed redirect, 5xx retry, no retry on 403, untrusted links | `tests/test_failures.py`, `tests/test_untrusted.py` | Live 403 without `Accept` documented in `access.md` |

## Live extras (not required for `pytest`)

See `live-retrieval.md`. Reviewer should treat:

- **Verified live:** Maaden English Integrated Report 2025 PDF GET, hash, path, page identity/period.
- **Verified live failure:** `statementsTabData` HTTP 500; listing unavailable.
- **Unverified live:** Aramco `fsPdf` download; other periods/languages; market-wide coverage.
- **Untested by design:** Google Finance identifier verification (slice 03).
