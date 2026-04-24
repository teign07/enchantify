#!/usr/bin/env python3
"""
tick_queue_utils.py — shared helpers for keeping memory/tick-queue.md bounded.
"""

from pathlib import Path

MAX_BYTES = 60000
KEEP_SECTIONS = 80


def ensure_header(path: Path, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(header, encoding="utf-8")


def prune_tick_queue(path: Path, header: str, max_bytes: int = MAX_BYTES, keep_sections: int = KEEP_SECTIONS) -> bool:
    if not path.exists():
        return False

    text = path.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) <= max_bytes:
        return False

    normalized_header = header.rstrip() + "\n\n"
    body = text
    if text.startswith("# Tick Queue"):
        parts = text.split("\n## ", 1)
        if len(parts) == 2:
            body = "## " + parts[1]
        else:
            body = ""

    if not body.strip():
        path.write_text(normalized_header, encoding="utf-8")
        return True

    chunks = body.split("\n## ")
    rebuilt = []
    for idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        rebuilt.append(("## " if idx > 0 or not chunk.startswith("## ") else "") + chunk.lstrip())

    kept = rebuilt[-keep_sections:]
    new_text = normalized_header + "\n".join(kept).strip() + "\n"
    path.write_text(new_text, encoding="utf-8")
    return True
