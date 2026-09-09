# Access evidence — Saudi Exchange report retrieval

Observed: 2026-09-09 (UTC). Client: Python 3.12 `urllib` and headless Google Chrome (Playwright `channel=chrome`) from this workspace. Host: `www.saudiexchange.sa`.

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
   - From urllib, GET and POST of that constructed URL (after a 200 profile GET, with cookies, `Referer`, and `X-Requested-With`) still returned **HTTP 500** body: `Error 500: CWSRV0295E: Error reported: 500`. This is a WebSphere error, not an empty report list.
   - Do not label `statementsTabData` an official API.

4. **Browser-driven tab listing (permitted alternative when urllib AJAX 500s)**
   - Headless Chrome opens the same company-profile URL on `www.saudiexchange.sa`, clicks `#finacialStatementAndReports`, and waits for `a[href*='/Resources/fsPdf/']`.
   - The live table is a **year-column matrix** (2026…2022) with row labels Annual / Q1–Q4 / Board Report (Arabic: **سنوي** / **الربع الأول–الرابع**). PDF icons are empty-text `<a class="btn-pdf">` links; language is `_En.pdf` on `locale=en` and `_Ar.pdf` on `locale=ar` (not both languages in one table).
   - Playwright captures that HTML; it is parsed as untrusted data. Filenames are copied from observed `href`s. None were invented.
   - Live counts on 2026-09-09: Maaden `1211` **44** `/Resources/fsPdf/` rows (22 English + 22 Arabic); Aramco `2222` **44** rows (same split). urllib `statementsTabData` remained 500 in the same sessions.
   - PDF bytes are **not** downloaded by the browser. Downloads still use urllib, allowed hosts, and `storage/reports/`.

5. **Original PDF objects**
   - Path pattern on the same host: `https://www.saudiexchange.sa/Resources/fsPdf/{issuer}_{code}_{YYYY-MM-DD}_{HH-MM-SS}_{En|Ar}.pdf`
   - Live listing → selection → download (Maaden 2025 annual English financial statements):  
     `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf`  
     HTTP **200**, `Content-Type: application/pdf`, body starts `%PDF-1.7`, **8,681,557** bytes, SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`.
   - This URL was copied from the live Financial Statements **Annual / 2025** cell after the tab click. It is not the Board Report / Integrated Report object `370_0_2026-03-29_11-05-45_En.pdf` (that row is typed `other` on the same table).
   - A prior `retrieve-url` of the Integrated Report remains on disk from disp-01-impl-001; that path does not satisfy D3 by itself.

## Access conditions actually observed

| Client | Headers | Result |
|---|---|---|
| `curl` HTTP/1.1 or HTTP/2 | Chrome UA or library UA | **403** Akamai `Access Denied` (`errors.edgesuite.net`, `Akamai-Cache-Status: Error from child`) |
| Python `urllib` | `User-Agent` only, **no `Accept`** | **403** |
| Python `urllib` | `User-Agent` + **`Accept: */*`** | **200** (watch, profile, PDF); `statementsTabData` **500** |
| Playwright + system Chrome | Chrome UA + `Accept: */*` | Profile **200**; tab click populates `/Resources/fsPdf/` rows. Occasional Akamai **Access Denied** title if UA/headers omitted; retried. |

Library UA used for urllib: `SaudiExchangeReports/0.1 (+local research; slice-01 original-PDF retrieval)`. Browser listing uses a Chrome UA so the public page's own JS can run.

This is ordinary public HTTP plus clicking a public tab. It is not a documented API key and not an attempt to bypass login. Akamai still blocks some HTTP stacks (curl from this IP) while allowing stdlib urllib and Chrome.

Retries: HTTP 429/5xx are retried with backoff; **403 is not retried**. Redirects are followed only onto `www.saudiexchange.sa` / `saudiexchange.sa`. Downloads are constrained to `/Resources/fsPdf/*.pdf` and `storage/reports/` (gitignored). Browser navigation is likewise limited to those hosts.

## Limitations

- No verified official reports API. `statementsTabData` is website AJAX and still HTTP 500 from urllib.
- Browser listing requires Playwright and a local Chrome (`channel=chrome`). `retrieve --no-browser` keeps the urllib-only path (listing unavailable while the AJAX 500s).
- English and Arabic PDFs are on **separate locale tables**, not mixed icons in one row.
- An Aramco `/Resources/fsPdf/` listing was obtained live (issuer `1541`); no Aramco PDF was downloaded in this repair.
- Profile locale follows `locale=` / `LanguageCookie`.
- WebSphere portlet tokens (`!ut/p/z1/...`, `IZ7_…`) are session/site rewrite values; they can change. Browser requests use a different rewritten path than the static `<base href>` urllib URL.
- Successful PDF GET is not proof that every listed company or period is downloadable from this IP or client.
