# D2 — Verified Google mappings on existing identities

No second company table. `company_id` remains `sa-tdwl-2222` and `sa-tdwl-1211`. `SaudiExchangeIdentifiers` is unchanged. Google fields live on `CompanyIdentity.google_finance`.

## Verified Tadawul mappings (implementation 2026-09-09)

Confirmed with `verify_quote_page` against a live Google Finance quote page (title + final URL). Classic `/finance/quote/SYMBOL:EXCHANGE` URLs follow redirect to `/finance/beta/quote/…`.

| Shared identity | Ticker | `quote_symbol` | `exchange` | `quote_id` | Classic URL | Final path | Page title observed | `verified` |
|---|---|---|---|---|---|---|---|---|
| `sa-tdwl-2222` | `2222` | `2222` | `TADAWUL` | `2222:TADAWUL` | `https://www.google.com/finance/quote/2222:TADAWUL` | `/finance/beta/quote/2222:TADAWUL` | `Saudi Arabian Oil Co (2222) Stock Price & News - Google Finance` | `True` |
| `sa-tdwl-1211` | `1211` | `1211` | `TADAWUL` | `1211:TADAWUL` | `https://www.google.com/finance/quote/1211:TADAWUL` | `/finance/beta/quote/1211:TADAWUL` | `Saudi Arabian Mining Company SJSC (1211) Stock Price & News - Google Finance` | `True` |

## Rejected: `*:SAU`

Live `https://www.google.com/finance/quote/2222:SAU` (2026-09-09) redirected to `/finance/beta/quote/2222:SAU` with page title `Google Finance` (no company name). `verify_quote_page` returns `REJECTED`. Catalog does not store `2222:SAU` or `1211:SAU` as verified mappings. Identical numeric tickers on another venue are not treated as the same company.

## Fail-closed identity (unchanged from slice 01)

Synthetic tests in `tests/test_identity.py` and `tests/test_google_mapping.py`:

- Arabic/English/ticker still resolve to the same `company_id`.
- Ambiguous name `Saudi Arabian` stays `AMBIGUOUS` (Google must not pick).
- Conflicting name+ticker (`Saudi Aramco` + `1211`) stays `CONFLICTING`.
- NASDAQ `2222` stays `WRONG_EXCHANGE`.
- Unknown ticker stays `NOT_FOUND`.
- Related-security mention of `1211` on an Aramco quote HTML fixture does not swap identity.

HTML bodies used in tests are hand-written titles/mappings, not live dumps.
