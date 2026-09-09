# D7 — Commands, fixture vs live vs stored-PDF

Routine pytest uses **hand-written** earnings/financials fixtures (`tests/google_fixtures.py`) and existing synthetic Google HTML. Invented figures (for example revenue `1234000000`, display `1.23B` / `10.64B`) are not live Google dumps. Published Maaden FS originals used as **PDF fixture strings** (and as matching Google fixture values for match cases) are from the stored filing, not from a committed Google payload.

Live Google response bodies are **not** in this file. Optional dumps stay under gitignored `evidence/live-payloads/`.

LICENSE/LEGAL at the pin were re-read at implementation: LICENSE SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`, LEGAL.md SHA-256 `51dac106bb00d1c896f8c04cc6e39211f715a4e13a13700f8057bc68594e4048` (match `evidence/03-google-overview/notices.md`).

## Routine tests (no Google network)

From `/workspace/saudi-exchange-mcp`:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ --override-ini addopts= -q
```

Result (2026-09-09, disp-04-impl-001): **151 passed, 6 skipped**.

The six skipped tests are marked `live_google` (three slice 03 overview/news/profile + three slice 04 earnings/financials). Default pytest autouses an httpx get/post block unless that marker is present. Stored-PDF Maaden tests ran because the gitignored FS was present (they skip if absent).

Slice 01–03 tests remain in this count.

## Opt-in live Aramco (labelled live, not fixture)

```bash
SAUDI_LIVE_GOOGLE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/ -m live_google --override-ini addopts= -q
```

Result: **6 passed** (3 slice 03 + 3 slice 04). No golden live EPS/revenue.

Field-presence (live, 2026-09-09; **no live JSON/HTML committed**):

| Check | Outcome |
|---|---|
| Earnings identity | `2222` / `2222:TADAWUL` |
| Currency | `SAR` |
| Periods | ≥1 quarterly row; actual vs estimate labelled when present; missing actuals `unavailable` not `0` |
| Alternate earnings | advertised; identical to primary → not double-counted |
| Earnings HTML | still `Loading Previous Earnings...` while dataset populated |
| Income statement | annual **and** quarterly returned; original Google labels present |
| Balance sheet / cash flow | retrieved from Financials purpose; display labels gapped |
| Inventory | earnings/financials `product=support` |

## Stored-PDF (Maaden 2025 annual English FS)

SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`. Comparison outcomes: `evidence/04-google-financials/maaden-pdf-crosscheck.md`. Fixture comparison (no network) uses the published PDF originals as fact strings.

## Snapshot commands

```bash
python3 loop/identity.py snapshot loop/manifests/candidate.json
```

## Git audit

`evidence/live-payloads/` is gitignored and must not appear in `git ls-files`. Synthetic fixtures must not contain live batchexecute dumps.
