# Access evidence — Saudi Exchange report retrieval

Observed: 2026-09-09 (UTC). Client: Python 3.12 `urllib` from this workspace (`34.210.205.116`). Host: `www.saudiexchange.sa`.

This is **not** an official public reports API. No documented partner/open-data reports endpoint was verified on the live site during this slice. Paid third parties (eReference Data, Argaam, and similar) were not used.

## Permitted route (website, as observed)

1. **Main Market Watch**
   - Arabic: `https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch?locale=ar`
   - English: `https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch?locale=en`
   - HTTP **200** with stdlib urllib when `User-Agent` and `Accept: */*` are sent.
   - Page JavaScript sets Main Market company-profile URLs as  
     `/wps/portal/saudiexchange/hidden/company-profile-main/!ut/p/z1/<token>/?companySymbol=`  
     The same `z1` token was used for symbols `2222` and `1211`.

2. **Company profile** (discovery authority for the company)
   - Pattern: `https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziTR3NDIw8LAz83d2MXA0C3SydAl1c3Q0NvE30I4EKzBEKDMKcTQzMDPxN3H19LAzdTU31w8syU8v1wwkpK8hOMgUA-oskdg!!/?companySymbol={SYMBOL}`
   - Optional `&locale=ar` or `en` (otherwise IBM `LanguageCookie` / hidden `requestLocale` apply).
   - Live GETs (200, ~1.0–1.1 MiB HTML):
     - `?companySymbol=1211` — English heading **Saudi Arabian Mining Co.**, short **MAADEN**; Arabic legal name **شركة التعدين العربية السعودية**, short **معادن**.
     - `?companySymbol=2222` — English **Saudi Arabian Oil Co.** / **SAUDI ARAMCO**; Arabic `locale=ar` heading **شركة الزيت العربية السعودية**; **أرامكو** present; sector **الطاقة**.
   - Tab label (site typo): `id="finacialStatementAndReports"` — English **FINANCIAL STATEMENTS AND REPORTS**, Arabic **القوائم المالية والتقارير**.
   - Static profile HTML **does not** contain `/Resources/fsPdf/` links. A by-laws PDF may appear under `/Resources/pdfs/{issuer}_ByLaw*.pdf` (Maaden `370_ByLaw2.pdf`, Aramco `1541_ByLaw1.pdf`). Those are not financial statements.

3. **Financial Statements and Reports table (browser AJAX, not an API)**
   - Click handler calls `renderTabDataV2(..., stmtType=6, reportType=0)`.
   - jQuery GET relative URL (from profile `<script>`):  
     `p0/IZ7_5A602H80O0VC4060O4GML81G57=CZ6_5A602H80OGF2E0QF9BQDEG10K4=NJstatementsTabData=/`
   - Query: `statementType=6&reportType=0&requestLocale={en|ar}&symbol={SYMBOL}`
   - Absolute URL is `urljoin(<base href>, relative)`. Live `<base href>` used a **z0** token that differs from the `z1` profile path.
   - From this client, GET and POST of that URL (after a 200 profile GET, with cookies, `Referer`, and `X-Requested-With`) returned **HTTP 500** body: `Error 500: CWSRV0295E: Error reported: 500`. This is a WebSphere error, not an empty report list.
   - Do not label `statementsTabData` an official API.

4. **Original PDF objects**
   - Path pattern on the same host: `https://www.saudiexchange.sa/Resources/fsPdf/{issuer}_{code}_{YYYY-MM-DD}_{HH-MM-SS}_{En|Ar}.pdf`
   - Live retrieval (this session):  
     `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf`  
     HTTP **200**, `Content-Type: application/pdf`, body starts `%PDF-1.6`, **10,216,122** bytes, SHA-256 `dae44e050e70e412049516a4caea688f9ff0cd918cab44b393ee86ecaf4b02a6`.
   - This URL was requested as a known `/Resources/fsPdf/` object on the verified host. It was **not** copied from live `statementsTabData` HTML in this environment (that call 500s). Filename `370` matches the Maaden profile by-laws issuer id. The PDF itself is **Maaden — Integrated Report 2025** (see `live-retrieval.md`). Filenames for other periods/companies were not invented.

## Access conditions actually observed

| Client | Headers | Result |
|---|---|---|
| `curl` HTTP/1.1 or HTTP/2 | Chrome UA or library UA | **403** Akamai `Access Denied` (`errors.edgesuite.net`, `Akamai-Cache-Status: Error from child`) |
| Python `urllib` | `User-Agent` only, **no `Accept`** | **403** |
| Python `urllib` | `User-Agent` + **`Accept: */*`** | **200** (watch, profile, PDF) |

Library UA used: `SaudiExchangeReports/0.1 (+local research; slice-01 original-PDF retrieval)`.

This is ordinary public HTTP with an identifying UA and a required `Accept` header, not a documented API key and not an attempt to bypass login. Akamai still blocks some HTTP stacks (curl from this IP) while allowing stdlib urllib. Headless-browser impersonation was not used.

Retries: HTTP 429/5xx are retried with backoff; **403 is not retried**. Redirects are followed only onto `www.saudiexchange.sa` / `saudiexchange.sa`. Downloads are constrained to `/Resources/fsPdf/*.pdf` and `storage/reports/` (gitignored).

## Limitations

- No verified official reports API.
- Live listing of the Financial Statements and Reports table failed (`statementsTabData` HTTP 500). Fixture HTML covers parser/selection tests; it is not a live index dump.
- An Aramco `/Resources/fsPdf/` URL was not obtained live; issuer id `1541` is from the by-laws PDF path only. No Aramco financial-report PDF was downloaded.
- Profile locale follows `locale=` / `LanguageCookie`; English HTML does not contain the Arabic legal name.
- WebSphere portlet tokens (`!ut/p/z1/...`, `IZ7_…`) are session/site rewrite values; they can change.
- Successful PDF GET is not proof that every listed company or period is downloadable from this IP or client.
