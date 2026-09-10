# MCP `tools/list` (product)

Source: stdio `tools/list` after initialize on `python -m saudi_exchange_reports.mcp`. Fixed list (`tools.listChanged` false). SDK `mcp` 1.30.0.

None of: `google_finance_call_rpc`, `google_finance_call_dataset`, `google_finance_call_quote_dataset`, `google_finance_batch_call`, `google_finance_get_quote_holdings`, generated `google_finance_ds_*`, `google_crosscheck`.

| Tool | Source phrase in description |
|---|---|
| `lookup_company` | Shared identity lookup; both Saudi Exchange and Google Finance identifier blocks; not a Google-only tool |
| `google_overview` | Google Finance overview/quote/statistics; unknown freshness is not real-time |
| `google_news` | Google Finance security news; publisher/URL/time; read_status |
| `google_profile` | Google Finance profile/about |
| `google_earnings` | Google Finance actual versus estimate; not an official filing |
| `google_financials` | Google Finance IS/BS/CF; `display_label_gap` for unverified BS/CF labels |
| `google_coverage` | Google Finance coverage/gaps; does not merge PDF figures |
| `research_company` | Google-only compose; does not retrieve official PDFs |
| `list_official_reports` | Saudi Exchange original reports (website listing, not an official API) |
| `download_official_report` | Saudi Exchange `/Resources/fsPdf/` original PDF |
| `read_official_report` | Stored original Saudi Exchange PDF; 1-based PDF page indices |
| `search_official_report` | Stored original Saudi Exchange PDF; empty search is `not_found` |
| `find_official_line_item` | Stored original Saudi Exchange PDF line; missing is not zero |

Initialize `instructions` include: Google Finance is primary for everyday company questions and structured tables; Saudi Exchange PDFs are for official reports, notes, and original evidence; installing MCP does not itself perform research; unknown quote freshness is not real-time; Google tables are not audited filings; PDF page citations apply only to PDF-derived facts.
