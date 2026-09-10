# D6 — Public-section inventory (2026-09-09)

Inventory is produced from the live quote page's `AF_initDataKeys` / `AF_dataServiceRequests` via the pinned metadata compiler (`purpose` from rpc-id and request shape). Product APIs select by **purpose name**, not a frozen `ds:3` = quote (on these pages `ds:3` is **Equity sectors**; quote summary is `ds:4`).

Live RPC ids are **not** a stable ABI. Examples observed for required purposes (Aramco and Maaden matched): quote summary `gCvqoe`, company profile `JL8oKc`, security news `wdVNWe`, security overview `ADgT7b`. CLI JSON omits RPC ids (`product_api_hides_rpc_ids`).

Aramco source URL (final): `/finance/beta/quote/2222:TADAWUL`. Maaden: `/finance/beta/quote/1211:TADAWUL`. Both advertised `ds:0`–`ds:24` (README at the pin documents `ds:0`–`ds:23`).

## Section table

| Purpose (upstream compiler) | Live key (Aramco/Maaden) | Slice 03 product | Notes |
|---|---|---|---|
| Quote summary | `ds:4` | **Support** (overview) | Alternate `ds:17`. Primary quote payload. |
| Quote summary alternate | `ds:17` | **Support** (overview fallback) | Same rpc family, no trailing mode flag. |
| Security overview card | `ds:11` | **Support** as labelled statistics source | Alternate `ds:18`. Do not dump unlabelled vectors. |
| Security overview card alternate | `ds:18` | **Support** as labelled statistics source | |
| Market statistics | `ds:6`, `ds:16` | **Support** when non-empty; else unavailable | Live Aramco call of this purpose returned an **empty** `data` array. `previous_close` is therefore `unavailable` (the unlabelled quote-summary float is not treated as previous close). Labelled HTML supplied Open/High/Low, Mkt. cap, Volume, P/E, Dividend, 52-wk high/low. |
| Company profile | `ds:5` | **Support** (profile/about) | Payload + labelled About pairs on the quote page. |
| Security news feed | `ds:21` | **Support** (news) | Company/security feed. Headlines/snippets only; `read_status=not_read`. |
| Market news feed | `ds:20` | Observe | Not used as company news. Draft-time body was empty; not productized as company news. |
| Earnings history and estimates (and alternate) | `ds:9`, `ds:10` | **Support** (slice 04; alternate is fallback only, not a second feed) | Parsed as actual-versus-estimate quarterly history. Identical primary/alternate bodies are de-duplicated. |
| Financials / estimates | `ds:19` (live Aramco and Maaden 2026-09-09); mapping fixtures may use `ds:17` | **Support** (slice 04) | Selected by compiler purpose `Financials / estimates`, not a frozen `ds:N`. Income statement labels bound from the displayed table. Balance sheet and cash flow remain display-label unverified when those tables are not embedded. |
| Intraday / one-month charts (points and OHLCV) | `ds:12`–`ds:15` | Observe, not productized | No chart product. |
| Related securities | `ds:7` | Observe, not productized | Must not mutate identity. |
| Analyst ratings and price targets | `ds:8` | Observe, not productized | |
| Equity sectors | `ds:3` | Observe (page-global) | This is why `ds:3` must not be hardcoded as quote. |
| Market overview quotes | `ds:0` | Observe (page-global) | |
| Empty / no-frame initialization | `ds:1`, `ds:2`, `ds:22`, `ds:23`, `ds:24` | Record as non-data | Includes live `ds:24`. |
| Quote Holdings RPC `K5Y6Xb` | (not in `ds:*`) | Out of product | Not exposed. |
| Google Finance AI chat, portfolios, watchlists, Compare/Options UI, Sign-in | UI only | Out of product | |
| Visible Financials / Earnings / Income statement / Balance sheet / Cash flow tabs | Present on page | Inventory as present; retrieval/parsing is slice 04 | |

## How to emit

Library: `get_inventory("ARAMCO")`. CLI: `python3 -m saudi_exchange_reports google-inventory ARAMCO --format json`.

Synthetic fixture inventory (no network) is in `tests/test_google_inventory.py`: required purposes, **supported** earnings/financials, empty init, empty market statistics, quote key ≠ `ds:3`.
