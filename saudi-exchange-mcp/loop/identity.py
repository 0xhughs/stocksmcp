#!/usr/bin/env python3
"""Reproducible snapshot and contract identity for LOOP.md."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = Path(__file__).resolve().parent / "manifests"

EXCLUSION_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".tox",
    "manifests",
}

EXCLUSION_PATH_PREFIXES = (
    "storage/",
    "loop/manifests/",
    "evidence/live-payloads/",
)

EXCLUSION_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".DS_Store",
)

# Coordinator session notes; Loop bookkeeping lives in BUILD/SLICES and is normalized.
BOOKKEEPING_FILES = {
    "HANDOFF.md",
}

SLICE_EXCLUDE_HEADINGS = {
    "run status",
    "shipped",
    "release evidence",
}

BUILD_EXCLUDE_HEADINGS = {
    "proof",
    "review",
    "loop state",
    "status",
    "next",
}

SNAPSHOT_FIELD_PREFIXES = (
    "Snapshot capture command:",
    "Snapshot recheck command:",
    "Snapshot coverage:",
    "Snapshot exclusions:",
)


def is_excluded(rel: str) -> bool:
    parts = Path(rel).parts
    if any(part in EXCLUSION_DIR_NAMES for part in parts):
        return True
    if any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in EXCLUSION_PATH_PREFIXES):
        return True
    return rel.endswith(EXCLUSION_SUFFIXES)


def iter_covered_files() -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
        rel_dir = os.path.relpath(dirpath, ROOT)
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = [
            d
            for d in dirnames
            if d not in EXCLUSION_DIR_NAMES
            and not is_excluded(str(Path(rel_dir) / d) if rel_dir else d)
        ]
        for name in filenames:
            rel = str(Path(rel_dir) / name) if rel_dir else name
            rel = rel.replace(os.sep, "/")
            if is_excluded(rel) or rel in BOOKKEEPING_FILES:
                continue
            files.append(Path(dirpath) / name)
    files.sort(key=lambda p: str(p.relative_to(ROOT)).replace(os.sep, "/"))
    return files


def file_record(path: Path) -> dict:
    rel = str(path.relative_to(ROOT)).replace(os.sep, "/")
    st = path.lstat()
    mode = stat.S_IMODE(st.st_mode)
    executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    if stat.S_ISLNK(st.st_mode):
        return {
            "path": rel,
            "type": "symlink",
            "target": os.readlink(path),
            "mode": f"{mode:04o}",
            "executable": executable,
            "sha256": None,
            "size": None,
        }
    if not stat.S_ISREG(st.st_mode):
        return {
            "path": rel,
            "type": "other",
            "target": None,
            "mode": f"{mode:04o}",
            "executable": executable,
            "sha256": None,
            "size": st.st_size,
        }
    data = snapshot_bytes(path, rel)
    return {
        "path": rel,
        "type": "file",
        "target": None,
        "mode": f"{mode:04o}",
        "executable": executable,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }


def snapshot_bytes(path: Path, rel: str) -> bytes:
    """Hash protocol files without mutable Loop bookkeeping so state-only writes keep identity."""
    if rel == "BUILD.md":
        return extract_build_header_and_criteria(path.read_text(encoding="utf-8")).encode("utf-8")
    if rel == "SLICES.md":
        return extract_slices_contract(path.read_text(encoding="utf-8")).encode("utf-8")
    return path.read_bytes()


def snapshot_payload() -> dict:
    records = [file_record(p) for p in iter_covered_files()]
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return {
        "root": "saudi-exchange-mcp",
        "file_count": len(records),
        "digest": digest,
        "files": records,
    }


def split_markdown_sections(text: str) -> list[tuple[str, str, str]]:
    lines = text.splitlines(keepends=True)
    sections: list[tuple[str, str, str]] = []
    current_heading = ""
    current_level = ""
    buf: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if buf or current_heading:
                sections.append((current_level, current_heading, "".join(buf)))
            current_level = "##"
            current_heading = line[3:].strip()
            buf = [line]
        else:
            buf.append(line)
    if buf or current_heading:
        sections.append((current_level, current_heading, "".join(buf)))
    return sections


def extract_slices_contract(text: str) -> str:
    parts: list[str] = []
    for _level, heading, body in split_markdown_sections(text):
        if heading.lower() in SLICE_EXCLUDE_HEADINGS:
            continue
        if heading.lower() in {"now", "later"}:
            # Placement headers are bookkeeping; keep mapped slice bodies.
            without_header = "".join(body.splitlines(keepends=True)[1:])
            parts.append(without_header)
            continue
        parts.append(body)
    return "".join(parts)


def extract_build_header_and_criteria(text: str) -> str:
    parts: list[str] = []
    for _level, heading, body in split_markdown_sections(text):
        if heading.lower() in BUILD_EXCLUDE_HEADINGS:
            continue
        parts.append(body)
    snapshot_lines = []
    in_loop = False
    for line in text.splitlines():
        if line.strip() == "## Loop state":
            in_loop = True
            continue
        if in_loop and line.startswith("## "):
            break
        if in_loop:
            stripped = line.strip()
            if any(stripped.startswith(prefix) for prefix in SNAPSHOT_FIELD_PREFIXES):
                snapshot_lines.append(stripped + "\n")
    return "".join(parts) + "".join(snapshot_lines)


def contract_payload() -> dict:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    slices = extract_slices_contract((ROOT / "SLICES.md").read_text(encoding="utf-8"))
    build = extract_build_header_and_criteria((ROOT / "BUILD.md").read_text(encoding="utf-8"))
    loop = (ROOT / "LOOP.md").read_text(encoding="utf-8")
    builder = (ROOT / "BUILDER.md").read_text(encoding="utf-8")
    reviewer = (ROOT / "REVIEWER.md").read_text(encoding="utf-8")
    documents = {
        "AGENTS.md": agents,
        "SLICES.md#contract": slices,
        "BUILD.md#contract": build,
        "LOOP.md": loop,
        "BUILDER.md": builder,
        "REVIEWER.md": reviewer,
    }
    canonical = json.dumps(documents, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "digest": hashlib.sha256(canonical).hexdigest(),
        "documents": {name: hashlib.sha256(body.encode("utf-8")).hexdigest() for name, body in documents.items()},
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {"snapshot", "contract"}:
        print("usage: identity.py snapshot|contract [output.json]", file=sys.stderr)
        return 2
    kind = argv[1]
    payload = snapshot_payload() if kind == "snapshot" else contract_payload()
    default_name = "snapshot.json" if kind == "snapshot" else "contract.json"
    out = Path(argv[2]) if len(argv) > 2 else MANIFEST_DIR / default_name
    if not out.is_absolute():
        out = Path.cwd() / out
    write_json(out, payload)
    print(f"{kind}_digest={payload['digest']}")
    print(f"path={out}")
    if kind == "snapshot":
        print(f"file_count={payload['file_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
