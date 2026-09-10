# One-connection MCP session log

Proof host: in-workspace MCP Python SDK client (`ClientSession` / `stdio_client`) launching `python -m saudi_exchange_reports.mcp`. Not Cursor desktop UI. Not library `get_overview()` / `extract_report()` without JSON-RPC.

Protocol: initialize (`initialize` + `notifications/initialized`), `tools/list`, `tools/call`. stdout is JSON-RPC only.

## Labelling

| Layer | What |
|---|---|
| **Fixture stdio** | Default pytest `tests/test_mcp_server.py`. `ScriptedSource` + `FakeTransport`. No live Google. Synthetic PDF. |
| **Live Google** | Opt-in `SAUDI_LIVE_GOOGLE=1` `tests/test_mcp_live.py` and `tests/record_mcp_session.py`. Field-presence only below. Bodies in gitignored `evidence/live-payloads/` if dumped. |
| **Stored-PDF** | Gitignored Maaden 2025 annual English FS. Read/search through MCP. |

## Fixture stdio (default pytest) — four classes, one connection

Test: `test_four_prompt_classes_on_one_scripted_connection`.

| Class | Tools on the same connection | Arguments (no bodies) | Presence |
|---|---|---|---|
| Lookup (D2 + D5 Arabic/English) | `lookup_company` | query Arabic Aramco; query `Saudi Aramco` | both `matched`, `sa-tdwl-2222` |
| Broad | `research_company` | query `ARAMCO` | source `google_finance`; sections overview/news/profile/earnings + IS; BS/CF retrieved or gapped; `pulled_official_pdfs` false; no `page_number` |
| Targeted | `google_overview`, `google_news`, `google_profile`, `google_earnings`, `google_financials` × IS/BS/CF | query `ARAMCO`; statement+frequency | overview last/currency/source/retrieved_at/freshness; news publisher/url; Google labels not IFRS |
| Official report | `list_official_reports`, `download_official_report`, `read_official_report`, `search_official_report` | query `MAADEN`; period `2025`; path from download | source `saudi_exchange`; search hit page 1 on synthetic PDF |
| Combined | `google_overview` + `search_official_report` | ticker `2222` + Maaden PDF search | sources `google_finance` and `saudi_exchange` separately |

Also on other scripted sessions: identity failures as structured results (`isError` false); Google outage then successful list; listing unavailable then Google overview; Google tools write no files under storage; report tools do not construct `LiveGoogleSource`; HTML-as-PDF `failed`/`InvalidPdf`; off-storage read `UnsafeDestination`; unknown tool JSON-RPC error.

## Live stdio (2026-09-09) — four classes, one connection

Command: `SAUDI_LIVE_GOOGLE=1 .venv/bin/python -m pytest tests/test_mcp_live.py` (1 passed) and the recorder. No live prices copied here.

`tools/list` names: `lookup_company`, `google_overview`, `google_news`, `google_profile`, `google_earnings`, `google_financials`, `google_coverage`, `research_company`, `list_official_reports`, `download_official_report`, `read_official_report`, `search_official_report`, `find_official_line_item`.

| Class | Tool | Arguments | Presence / provenance |
|---|---|---|---|
| Lookup | `lookup_company` | Arabic Aramco; `Saudi Aramco` | both `matched`; `sa-tdwl-2222`; `2222:TADAWUL` |
| Broad + targeted | `google_overview` | `ARAMCO` | source `google_finance`; last/currency/source_url/retrieved_at/quoted_at/freshness present; `is_realtime` false; `previous_close` unavailable |
| Broad + targeted | `google_news` | `ARAMCO` | source `google_finance`; items present |
| Broad + targeted | `google_profile` | `ARAMCO` | source `google_finance`; headquarters unavailable when missing |
| Broad + targeted | `google_earnings` | `ARAMCO` | source `google_finance`; periods present |
| Targeted financials | `google_financials` | IS quarterly/annual; BS annual; CF annual | IS periods returned, `display_label_gap` false; BS/CF periods returned, `display_label_gap` true |
| Official report | `list_official_reports` | `MAADEN` | source `saudi_exchange`; **live listing `unavailable`** (`from_cache` false). Documented skip of live listing only. |
| Official report | `read_official_report` | stored path, pages `19` | source `saudi_exchange`; hash `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`; page 19 native; notes heading present |
| Official report | `search_official_report` | query `share capital`, pages `19` | `found`; hit pages `[19, 19]`; not a Google table |
| Combined | `google_overview` + `search_official_report` | `2222` + stored Maaden search | sources `google_finance` then `saudi_exchange` on the **same** connection |

Cursor install is documented only (`cursor-mcp.json.example` + README). Not deployed.

## Isolation reminders

Google tools do not write `storage/reports/`. Report tools do not construct `LiveGoogleSource`. Public JSON `source` is `google_finance` or `saudi_exchange` (lookup uses `shared_identity`). PDF `page_number` only on report-reading results.
