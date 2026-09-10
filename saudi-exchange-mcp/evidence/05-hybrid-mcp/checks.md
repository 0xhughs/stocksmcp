# D7 — Slice 05 checks (2026-09-09)

Product stdio MCP wrapping shipped slices 01–04. Product entry: `python -m saudi_exchange_reports.mcp` / `saudi-exchange-mcp`. Not `google_finance_mcp.server`. Official MCP Python SDK `mcp==1.30.0` (`mcp>=1.30,<2`). LICENSE/LEGAL at pin `319760998e60d4b060fb993b3dc8db94364b019c` still match `evidence/03-google-overview/notices.md`.

## Commands

Default pytest (offline to Google; no live Saudi website required):

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ --override-ini addopts= -q
```

Result: **178 passed, 7 skipped** (six prior `live_google` plus `tests/test_mcp_live.py`). Autouse `httpx` block remains unless `live_google` / `live_mcp`.

Opt-in live MCP (one stdio connection; live Google bodies stay gitignored):

```bash
SAUDI_LIVE_GOOGLE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/test_mcp_live.py --override-ini addopts= -q
```

Result: **1 passed**. Field-presence recorder (output under gitignored `evidence/live-payloads/`):

```bash
SAUDI_LIVE_GOOGLE=1 PYTHONPATH=src .venv/bin/python tests/record_mcp_session.py
```

## D1–D6 (default pytest speaks stdio JSON-RPC)

| Criterion | Result |
|---|---|
| D1 product stdio, initialize + tools/list + tools/call, not upstream tools | pass |
| D1 stdout JSON-RPC only; `tools.listChanged` false | pass |
| D1 GoogleFinanceClient still does not import `google_finance_mcp.server` | pass |
| D2 lookup via MCP Arabic/English/ticker + failures | pass |
| D3 Google tools via ScriptedSource; source label; unavailable≠0; no RPC ids | pass |
| D4 list/download/read/search via FakeTransport + synthetic PDF; stored Maaden when present | pass |
| D5 Cursor `mcp.json` example parses; scripted one-connection four classes | pass |
| D6 Google fail then report; report fail then Google; isolation; invalid PDF; unsafe path | pass |

## Live MCP (D5.B)

Same ClientSession: initialize, `tools/list`, `tools/call`. Four prompt classes on **one** connection. See `mcp-session.md`. No live quote numbers in this tree.

## Git audit

`evidence/live-payloads/` is gitignored. Tracked `evidence/05-hybrid-mcp/` contains commands, tool names, field-presence, source labels, coverage/gaps, PDF hash/page citations, and the Cursor example — not live Google bodies.
