# D7 — Commands, fixture vs live

Routine pytest uses **synthetic** HTML and hand-written batchexecute-shaped fixtures (`tests/google_fixtures.py`). Those values (price `12.34`, fixture news URL, fixture description) are invented. They are not live Google dumps.

Live Google response bodies are **not** in this file. Optional dumps stay under gitignored `evidence/live-payloads/`.

## Routine tests (no Google network)

From `/workspace/saudi-exchange-mcp`:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ --override-ini addopts= -q
```

Result (2026-09-09, disp-03-impl-001): **125 passed, 3 skipped**.

The three skipped tests are marked `live_google` (`test_live_aramco_overview_identity_not_price_golden`, `test_live_aramco_news_has_url`, `test_live_aramco_profile_has_description_or_website`). Default pytest autouses an httpx get/post block unless that marker is present.

Slice 01–02 tests remain in this count (identity, listing, retrieval, reading, OCR, CLI reading).

## Opt-in live Aramco (labelled live, not fixture)

```bash
SAUDI_LIVE_GOOGLE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/test_google_overview.py tests/test_google_news.py tests/test_google_profile.py -m live_google --override-ini addopts= -q
```

Result: **3 passed**.

Field-presence (live, 2026-09-09; **no prices or headlines recorded here**):

| Check | Outcome |
|---|---|
| Overview identity ticker / `quote_id` | `2222` / `2222:TADAWUL` |
| Currency | `SAR` present |
| Source URL | Google Finance quote page (final `/finance/beta/quote/2222:TADAWUL`) |
| Retrieval time | timezone-aware UTC present |
| Quote timestamp | present (`freshness=quoted_at`); timezone `Asia/Riyadh` |
| Session | labelled from payload date arrays when present |
| `is_realtime` | `False` (unknown/delayed freshness is not described as real-time) |
| Price number | present; **not** asserted as a golden value |
| Previous close | `unavailable` (not in labelled HTML; unlabelled payload float not used). Market statistics datasets empty. |
| News | ≥1 item with URL; publisher and time present on the first item; `article_body` is null; `read_status=not_read` |
| Profile | description present; website present; CEO/founded/employees/sector present; headquarters labelled `-` on the page → `unavailable` |

CLI (live, user-initiated; output not copied here):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports resolve ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-overview ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-news ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-profile ARAMCO --format json
PYTHONPATH=src python3 -m saudi_exchange_reports google-inventory ARAMCO --format json
```

## Git audit

`.gitignore` includes `evidence/live-payloads/`. Snapshot identity excludes that directory. Tracked tests contain only synthetic fixtures.

## D1–D2 tests (offline)

`tests/test_google_notices.py`, `tests/test_google_mapping.py`, `tests/test_identity.py` — included in the 125 passed above.
