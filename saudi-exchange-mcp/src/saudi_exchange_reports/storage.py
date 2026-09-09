"""Keep downloaded reports inside the configured storage directory."""

from __future__ import annotations

from pathlib import Path

from saudi_exchange_reports.errors import UnsafeDestination


def resolve_storage_root(storage_root: Path) -> Path:
    return storage_root.expanduser().resolve()


def ensure_within(storage_root: Path, destination: Path) -> Path:
    root = resolve_storage_root(storage_root)
    dest = destination.expanduser().resolve()
    try:
        dest.relative_to(root)
    except ValueError as exc:
        raise UnsafeDestination(f"{dest} is outside {root}") from exc
    return dest


def company_dir(storage_root: Path, ticker: str) -> Path:
    root = resolve_storage_root(storage_root)
    root.mkdir(parents=True, exist_ok=True)
    path = ensure_within(root, root / ticker)
    path.mkdir(parents=True, exist_ok=True)
    return path
