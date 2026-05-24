#!/usr/bin/env python3
"""Install the daily Listening Desk market research cron."""

from __future__ import annotations

import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
MARKER = "# Enchantify — Listening Desk market research"
ENTRY = (
    f"5 13 * * * cd {BASE} && "
    "/usr/bin/python3 scripts/market-research.py daily --send >> logs/publishing/market-research-cron.log 2>&1"
)


def main() -> int:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    text = current.stdout if current.returncode == 0 else ""
    lines = text.splitlines()
    kept: list[str] = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if line.strip() == MARKER:
            skip_next = True
            continue
        kept.append(line)
    kept.extend([MARKER, ENTRY])
    payload = "\n".join(kept).rstrip() + "\n"
    proc = subprocess.run(["crontab", "-"], input=payload, text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        return proc.returncode
    print("Installed Listening Desk market research cron:")
    print(ENTRY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
