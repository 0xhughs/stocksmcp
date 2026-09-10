# Vendored google-finance-mcp

This tree reuses [woodstock-tokyo/google-finance-mcp](https://github.com/woodstock-tokyo/google-finance-mcp)
**source** inspected at git commit `319760998e60d4b060fb993b3dc8db94364b019c`
(annotated tag `v0.1.4`, subject `fix: mapping table update`, 2026-08-23).
The `pyproject.toml` version string at this commit is still `0.1.3`.

## Documents (distinct)

- `LICENSE` — GNU GPL v3 (29 June 2007). Licenses **this software**, not Google
  Finance data, news, or exchange quotes. Re-read at implementation (2026-09-09)
  SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.
- `LEGAL.md` — developer usage/contribution policy. Unofficial; intended use is
  local, personal, manually configured, user-initiated. It **does not grant any
  license** to Google Finance or third-party market data. SHA-256
  `51dac106bb00d1c896f8c04cc6e39211f715a4e13a13700f8057bc68594e4048`.

A code license is not a data license. Google Terms of Service, the
[Google Finance disclaimer](https://www.google.com/googlefinance/disclaimer/),
and exchange/news-publisher terms remain separate.

## Modifications (2026-09-09)

Vendored into this Hybrid Pilot package rather than installing an unpinned
wheel or `master` clone:

- Copied `src/google_finance_mcp/*.py` into this repository's `src/google_finance_mcp/`.
- Preserved `LICENSE` and `LEGAL.md` here unchanged.
- Omitted upstream `docs/assets` GIF, packaging, CI workflows, and
  `src/google_finance_mcp.egg-info/` (not required to run the client).
- Slice 03 product code lives in `saudi_exchange_reports.google_finance` and
  imports `GoogleFinanceClient`; it does not import `google_finance_mcp.server`
  (MCP host wiring is slice 05). Routine tests therefore do not require the
  `mcp` package.

GPL-3.0 obligations for the covered work apply if/when this tree is conveyed.
This slice does not authorize a public release.
