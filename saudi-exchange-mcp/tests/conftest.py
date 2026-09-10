from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live-google",
        action="store_true",
        default=False,
        help="Allow live Google Finance HTTP (opt-in; default pytest stays offline).",
    )
    parser.addoption(
        "--live-mcp",
        action="store_true",
        default=False,
        help="Allow the live stdio MCP session (implies live Google HTTP).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live_google: hits Google Finance over the network; skipped unless --live-google or SAUDI_LIVE_GOOGLE=1",
    )
    config.addinivalue_line(
        "markers",
        "live_mcp: live stdio MCP session (Google + stored PDF); skipped unless --live-google/--live-mcp or SAUDI_LIVE_GOOGLE=1",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    enabled = (
        bool(config.getoption("--live-google"))
        or bool(config.getoption("--live-mcp"))
        or os.environ.get("SAUDI_LIVE_GOOGLE") == "1"
    )
    if enabled:
        return
    skip = pytest.mark.skip(reason="opt-in live Google: pass --live-google or SAUDI_LIVE_GOOGLE=1")
    for item in items:
        if "live_google" in item.keywords or "live_mcp" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _block_live_httpx(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    if request.node.get_closest_marker("live_google") or request.node.get_closest_marker("live_mcp"):
        yield
        return

    import httpx

    async def _blocked(*_a, **_k):
        raise AssertionError("default pytest must not hit Google; inject ScriptedSource")

    monkeypatch.setattr(httpx.AsyncClient, "get", _blocked)
    monkeypatch.setattr(httpx.AsyncClient, "post", _blocked)
    yield
