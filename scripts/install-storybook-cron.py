#!/usr/bin/env python3
"""Install Book of You daily and monthly cron entries idempotently."""

from __future__ import annotations

import subprocess


DAILY_MARKER = "# Enchantify — The Book of You: nightly illustrated storybook PDF"
DAILY_CMD = (
    "35 23 * * * cd /Users/bj/.openclaw/workspace/enchantify && "
    "/usr/bin/python3 scripts/storybook.py daily bj --send >> logs/storybook.log 2>&1"
)

MONTHLY_MARKER = "# Enchantify — The Book of You: monthly collected volume"
MONTHLY_CMD = (
    "55 23 28-31 * * cd /Users/bj/.openclaw/workspace/enchantify && "
    "[ $(date -v+1d +\\%d) = 01 ] && "
    "/usr/bin/python3 scripts/storybook.py monthly bj --month $(date +\\%Y-\\%m) --send >> logs/storybook.log 2>&1"
)


def main() -> int:
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    text = current.stdout if current.returncode == 0 else ""
    changed = False

    if DAILY_MARKER not in text:
        text = text.rstrip() + f"\n\n{DAILY_MARKER}\n{DAILY_CMD}\n"
        changed = True

    if MONTHLY_MARKER not in text:
        text = text.rstrip() + f"\n\n{MONTHLY_MARKER}\n{MONTHLY_CMD}\n"
        changed = True

    if not changed:
        print("Storybook cron entries already installed.")
        return 0

    proc = subprocess.run(["crontab", "-"], input=text, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        return proc.returncode
    print("Storybook cron entries installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
