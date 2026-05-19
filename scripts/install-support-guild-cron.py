#!/usr/bin/env python3
"""Install the daily Support Guild cron entry idempotently."""

from __future__ import annotations

import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
MARKER = "# Enchantify — support guild: daily council meeting"
ENTRY = (
    "10 8 * * * cd /Users/bj/.openclaw/workspace/enchantify && "
    "/usr/bin/python3 scripts/support-guild.py daily --send >> logs/support-faculty.log 2>&1"
)


def main() -> int:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    lines = current.stdout.splitlines() if current.returncode == 0 else []
    out: list[str] = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if line.strip() == MARKER:
            skip_next = True
            continue
        if "scripts/support-guild.py daily" in line:
            continue
        out.append(line)
    if out and out[-1].strip():
        out.append("")
    out.extend([MARKER, ENTRY])
    payload = "\n".join(out).rstrip() + "\n"
    proc = subprocess.run(["crontab", "-"], input=payload, text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        return proc.returncode
    print("Installed Support Guild cron:")
    print(ENTRY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
