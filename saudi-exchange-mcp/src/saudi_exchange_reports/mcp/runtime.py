"""Process-wide MCP runtime: storage, scripted transports, and optional test hooks."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from saudi_exchange_reports.google_finance.source import GoogleFinanceSource
from saudi_exchange_reports.http import Transport

DEFAULT_STORAGE = Path("storage/reports")


@dataclass
class Runtime:
    google_source: GoogleFinanceSource | None = None
    transport: Transport | None = None
    storage_root: Path = field(default_factory=lambda: DEFAULT_STORAGE)
    extra_allowed_roots: tuple[Path, ...] = ()
    min_interval_seconds: float = 1.0
    use_browser: bool = False


_RUNTIME: Runtime | None = None


def set_runtime(runtime: Runtime) -> None:
    global _RUNTIME
    _RUNTIME = runtime


def reset_runtime() -> None:
    global _RUNTIME
    _RUNTIME = None


def runtime_from_env() -> Runtime:
    storage = Path(os.environ.get("SAUDI_REPORTS_STORAGE", str(DEFAULT_STORAGE)))
    extra_raw = os.environ.get("SAUDI_MCP_EXTRA_ROOTS", "")
    extra = tuple(Path(p) for p in extra_raw.split(os.pathsep) if p)
    interval = float(os.environ.get("SAUDI_MCP_MIN_INTERVAL", "1.0"))
    use_browser = os.environ.get("SAUDI_MCP_USE_BROWSER", "0") == "1"
    return Runtime(
        storage_root=storage,
        extra_allowed_roots=extra,
        min_interval_seconds=interval,
        use_browser=use_browser,
    )


def get_runtime() -> Runtime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = runtime_from_env()
    return _RUNTIME


def apply_env_hook() -> None:
    hook = os.environ.get("SAUDI_MCP_HOOK")
    if not hook:
        return
    module_name, func_name = hook.rsplit(":", 1)
    module = importlib.import_module(module_name)
    getattr(module, func_name)()
