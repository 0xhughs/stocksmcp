# MCP-visible coverage (Aramco / Maaden)

Library coverage from slice 04 remains authoritative: `evidence/04-google-financials/coverage.md`. This file is what the **MCP tools** expose (`google_coverage` + section tools + official-report tools). Dated 2026-09-09.

Google tables are not audited originals. PDF page citations apply only to PDF-derived facts.

## Aramco (`2222` / `2222:TADAWUL`) — Google via MCP

| Section | Frequency | MCP-visible status |
|---|---|---|
| lookup | n/a | matched via English and Arabic on the live stdio session |
| overview / quote | live | `google_overview`: identity, currency, source_url, retrieved_at, quoted_at/freshness present; `is_realtime` false; `previous_close` may be unavailable |
| news | live | `google_news`: items with source Google Finance |
| profile / about | live | `google_profile`: description/website/CEO/founded/employees/sector; headquarters listed unavailable when missing |
| earnings | quarterly | `google_earnings`: periods present; `article_summary` null |
| income statement | quarterly | live `google_financials`: periods returned; `display_label_gap` false |
| income statement | annual | live: periods returned; `display_label_gap` false |
| balance sheet | annual | live: periods returned; `display_label_gap` true (unverified Google row names) |
| cash flow | annual | live: periods returned; `display_label_gap` true |

Fixture stdio (ScriptedSource) reproduces the same labels without network: IS display-verified; BS/CF `display_label_gap`.

## Maaden (`1211`) — official reports via MCP

| Capability | Fixture stdio | Live / stored-PDF |
|---|---|---|
| list | FakeTransport HTML → reports, `from_cache` false | live `list_official_reports` returned `unavailable` (website path; not treated as empty-market proof). Documented skip of **live listing only**. |
| download | Fake PDF → `downloaded` | not required once stored original is present; live listing skipped |
| read/search stored 2025 annual English FS | skip if gitignored file absent | **required and passed** via MCP `read_official_report` / `search_official_report` |

Stored original: SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`, source `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf`. MCP search `share capital` → page 19 native (notes). Google tables were not returned as that filing.

## Combined

Same live connection called `google_overview` (Google Finance) and `search_official_report` (Saudi Exchange PDF). Sources not merged. Quote date is not the reporting period.
