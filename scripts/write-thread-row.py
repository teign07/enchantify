#!/usr/bin/env python3
"""Safely add or update a row in world-register.md ## Active Threads."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
import sys


BASE = Path(__file__).parent.parent
REGISTER = BASE / "lore" / "world-register.md"
sys.path.insert(0, str(Path(__file__).parent))
from belief_caps import THREAD_CAP, clamp_belief


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("|", "/")).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Add/update an Active Threads row")
    parser.add_argument("name")
    parser.add_argument("belief", type=int)
    parser.add_argument("notes")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    text = REGISTER.read_text(encoding="utf-8")
    active_m = re.search(r"(?ms)^## Active Threads\s*\n(.*?)(?=^## |\Z)", text)
    if not active_m:
        raise SystemExit("Active Threads section not found")

    raw_belief = args.belief
    belief = clamp_belief(args.belief, "Thread", args.name)
    row = f"| {clean(args.name)} | Thread | {belief} | {clean(args.notes)} |"
    body = active_m.group(1)
    pattern = re.compile(rf"^\|\s*{re.escape(args.name)}\s*\|\s*Thread\s*\|\s*\d+\s*\|.*$", re.MULTILINE | re.IGNORECASE)
    if pattern.search(body):
        new_body = pattern.sub(row, body, count=1)
    else:
        # Insert after the table divider when possible, preserving existing order.
        lines = body.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if re.match(r"^\|\s*-", line):
                insert_at = i + 1
                break
        lines.insert(insert_at, row)
        new_body = "\n".join(lines)

    updated = text[:active_m.start(1)] + new_body.rstrip() + "\n\n" + text[active_m.end(1):].lstrip()
    if args.dry_run:
        print(row)
        if raw_belief != belief:
            print(f"[dry-run] Thread Belief capped at {THREAD_CAP} (requested {raw_belief})")
        return 0

    backup = REGISTER.with_suffix(".md.bak")
    shutil.copy2(REGISTER, backup)
    tmp = REGISTER.with_suffix(".md.tmp")
    tmp.write_text(updated if updated.endswith("\n") else updated + "\n", encoding="utf-8")
    tmp.rename(REGISTER)
    print(f"✓ Active thread row updated: {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
