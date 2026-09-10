# D6B — Maaden 2025 FS vs Google (dual provenance)

Google tables are **not** the audited original. PDF page citations apply only to PDF-derived facts. Google and PDF numbers are never merged into one “true” value.

Stored original: SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`, source `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf`. Currency: SAR / Saudi Riyals (stated). Scale: full riyals. Period: year ended / as at 31 December 2025. Scope: consolidated. Google UI B/M is display-only.

Slice 02 APIs used: `extract_report`, `find_line_item`, `search_extracted` (and `read_pages` available). Google side: `get_financials` / `get_crosscheck` parser (fixture in default pytest; live Maaden opt-in for implementation evidence).

CLI: `python3 -m saudi_exchange_reports google-crosscheck MAADEN --facts fixture` (default pytest path). Stored PDF: `--pdf storage/reports/1211/d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e.pdf --storage storage/reports`.

## Required pairs

| PDF original label (page) | PDF original | Outcome | Reason |
|---|---|---|---|
| `Revenue` (p.13) | `38,577,730,228` | **match** | Google **annual** 2025 Income statement `Revenue`, full SAR, same period-end. |
| `Profit for the year` (p.13) | `8,527,980,356` | **mismatch** | Google `Net income` is not this total (NCI). Labels kept separate. |
| `Ordinary shareholders of the parent company` (p.13) | `7,347,878,280` | **match** | Google `Net income` vs attributable-to-parent (cited separately). |
| `Basic and diluted earnings per share` (p.13) | `1.91` | **match** | Google annual `Earnings per share`. |
| `Total assets` (p.15) | `119,757,152,175` | **match** | Numeric agreement on an **unverified** Google slot vs PDF label. |
| `Total equity` (p.15) | `67,814,366,490` | **match** | Same; Google BS label unverified. |
| `Total liabilities` (p.15) | `51,942,785,685` | **match** | Same; Google BS label unverified. |
| `Net cash generated from operating activities` (p.17) | `10,927,067,206` | **match** | Numeric; Google CF label unverified. |
| `Net cash utilized in investing activities` (p.18) | `(10,120,345,838)` | **match** | Sign preserved (negative). |
| `Net cash utilized in financing activities` (p.18) | `(5,438,421,256)` | **match** | Sign preserved. |
| `Cash and cash equivalents` (p.15) | `10,583,548,481` | **mismatch** | Google cash line is not display-verified; PDF cash is not auto-identified with an unverified slot (different definition). |
| Notes share count (p.19) | `3,888,763,418` | **mismatch** | Google shares-outstanding-like slot is not issued share capital count. |

Quarterly Google vs annual PDF is **not_comparable** (fixture-covered). No Aramco PDF is required.

Live Maaden parser + stored PDF (opt-in, 2026-09-09) reproduced the same outcome classes. Live Google integers are not recorded here.
