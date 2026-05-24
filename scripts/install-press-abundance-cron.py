#!/usr/bin/env python3
"""Install Penny + Goldweaver daily Press & Applied Abundance cron."""

from __future__ import annotations

import subprocess


MARKER = "# Enchantify — press abundance: Penny + Goldweaver daily council"
ENTRY = (
    "35 13 * * * cd /Users/bj/.openclaw/workspace/enchantify && "
    "/usr/bin/python3 scripts/press-abundance.py daily bj --send >> logs/publishing/press-abundance-cron.log 2>&1"
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
        if "scripts/press-abundance.py daily" in line:
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
    print("Installed Press & Applied Abundance cron:")
    print(ENTRY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
