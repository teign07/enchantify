#!/usr/bin/env python3
"""Install Bellkeeper proactive cron entries idempotently."""

from __future__ import annotations

import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent

ENTRIES = [
    (
        "# Enchantify — Bellkeeper morning Today Page",
        "20 8 * * * cd /Users/bj/.openclaw/workspace/enchantify && /usr/bin/python3 scripts/bellkeeper.py today bj --send >> logs/support-faculty.log 2>&1",
        "scripts/bellkeeper.py today bj --send",
    ),
    (
        "# Enchantify — Bellkeeper upcoming event preparation",
        "*/30 7-21 * * * cd /Users/bj/.openclaw/workspace/enchantify && /usr/bin/python3 scripts/bellkeeper.py upcoming bj --send >> logs/support-faculty.log 2>&1",
        "scripts/bellkeeper.py upcoming bj --send",
    ),
    (
        "# Enchantify — Bellkeeper evening scrap for Book of You",
        "45 20 * * * cd /Users/bj/.openclaw/workspace/enchantify && /usr/bin/python3 scripts/bellkeeper.py evening bj --send >> logs/support-faculty.log 2>&1",
        "scripts/bellkeeper.py evening bj --send",
    ),
    (
        "# Enchantify — Bellkeeper week-ahead reading",
        "30 18 * * 0 cd /Users/bj/.openclaw/workspace/enchantify && /usr/bin/python3 scripts/bellkeeper.py week bj --send >> logs/support-faculty.log 2>&1",
        "scripts/bellkeeper.py week bj --send",
    ),
]


def main() -> int:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    text = current.stdout if current.returncode == 0 else ""
    lines = text.splitlines()
    changed = False
    for marker, command, needle in ENTRIES:
        if any(needle in line for line in lines):
            continue
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([marker, command])
        changed = True
    if not changed:
        print("Bellkeeper cron entries already installed.")
        return 0
    payload = "\n".join(lines).rstrip() + "\n"
    proc = subprocess.run(["crontab", "-"], input=payload, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        return proc.returncode
    print("Bellkeeper cron entries installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
