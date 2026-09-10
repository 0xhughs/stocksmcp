# D1 — Pinned google-finance-mcp notices

Slice 03 reuses [woodstock-tokyo/google-finance-mcp](https://github.com/woodstock-tokyo/google-finance-mcp) **source** at git commit `319760998e60d4b060fb993b3dc8db94364b019c` (annotated tag `v0.1.4`, subject `fix: mapping table update`, 2026-08-23). The `pyproject.toml` version string at this commit is still `0.1.3`.

In-tree copies:

| Path | Role |
|---|---|
| `vendor/google-finance-mcp/NOTICE.md` | Records the pin, tag/version mismatch, and how the tree was vendored. |
| `vendor/google-finance-mcp/LICENSE` | GNU GPL v3 (29 June 2007). Licenses **this software**, not Google Finance data. |
| `vendor/google-finance-mcp/LEGAL.md` | Usage/contribution policy. Unofficial; local, personal, user-initiated. **Does not grant any license** to Google Finance or third-party market data. |
| `src/google_finance_mcp/` | Vendored Python package (`GoogleFinanceClient` and helpers). `server.py` is present but **not imported** by slice 03 product code or routine tests. |
| `saudi_exchange_reports.google_finance.PINNED_REVISION` | Same commit string; tested in `tests/test_google_notices.py`. |

Re-read at implementation (2026-09-09):

- `LICENSE` SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`
- `LEGAL.md` SHA-256 `51dac106bb00d1c896f8c04cc6e39211f715a4e13a13700f8057bc68594e4048`

These match the BUILD.md draft-time hashes. The documents were not silently replaced with a newer policy.

## GPL vs data rights

A code license is not a data license. GPL-3.0 covers the reused/modified **code** when conveyed. Quotes, news, and profile text remain subject to Google Terms of Service, the [Google Finance disclaimer](https://www.google.com/googlefinance/disclaimer/), and exchange/publisher terms. This repository does not claim to license that data.

LEGAL.md additionally restricts *how* the software is used (no hosted market-data API, no redistribution of returned data, no committing live Google Finance responses). It is preserved unchanged under `vendor/google-finance-mcp/LEGAL.md`.

## Runtime

Added `httpx>=0.27` and `anyio>=4.0` (required by the pinned client). The `mcp` package is **not** a slice 03 dependency. Ordinary pytest imports `GoogleFinanceClient` and does not import `google_finance_mcp.server`.
