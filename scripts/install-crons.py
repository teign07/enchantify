#!/usr/bin/env python3
"""Install Enchantify cron entries idempotently.

The installer used to write a small old cron set directly from on-install.sh.
The modern Narrative OS has more rooms: pulse, simulation, support faculty,
Bellkeeper, Book of You, publishing/listening, Draw Things, and housekeeping.
This script is the single source of truth for those recurring jobs.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
PYTHON = os.environ.get("ENCHANTIFY_PYTHON", "/usr/bin/python3")


@dataclass(frozen=True)
class CronEntry:
    marker: str
    schedule: str
    command: str
    needle: str

    def line(self) -> str:
        return f"{self.schedule} {self.command}"


def q(value: str | Path) -> str:
    return shlex.quote(str(value))


def cd(command: str, log: str) -> str:
    inner = f"cd {q(BASE)} && {command}"
    return f"/bin/sh -lc {q(inner)} >> {q(BASE / log)} 2>&1"


def entries(player: str, *, telegram: bool = True, drawthings: bool = True) -> list[CronEntry]:
    send = " --send" if telegram else ""
    silent = " --telegram-silent" if telegram else ""
    drawthings_flags = f"--generate --keep-images 24{' --telegram --telegram-silent' if telegram else ''}"
    rows = [
        CronEntry(
            "# Enchantify — pulse: world heartbeat",
            "*/15 * * * *",
            cd(f"{q(PYTHON)} scripts/pulse.py", "logs/pulse.log"),
            "scripts/pulse.py",
        ),
        CronEntry(
            "# Enchantify — world: simulation and dispatch",
            "30 */3 * * *",
            cd(
                f"{q(PYTHON)} scripts/arc-tick.py && "
                f"{q(PYTHON)} scripts/tick.py && "
                f"{q(PYTHON)} scripts/world-pulse.py && "
                f"{q(PYTHON)} scripts/thread-steward.py --apply && "
                f"{q(PYTHON)} scripts/send_academy_dispatch.py",
                "logs/pulse.log",
            ),
            "scripts/world-pulse.py",
        ),
        CronEntry(
            "# Enchantify — schedule sync",
            "0 */3 * * *",
            cd(f"{q(PYTHON)} scripts/schedule.py --update-state", "logs/schedule.log"),
            "scripts/schedule.py --update-state",
        ),
        CronEntry(
            "# Enchantify — character outreach",
            "10 */2 * * *",
            cd(f"{q(PYTHON)} scripts/reach-out.py", "logs/reach-out.log"),
            "scripts/reach-out.py",
        ),
        CronEntry(
            "# Enchantify — nightly intelligence",
            "0 23 * * *",
            cd(f"{q(PYTHON)} scripts/labyrinth-intelligence.py {q(player)}", "logs/intelligence.log"),
            "scripts/labyrinth-intelligence.py",
        ),
        CronEntry(
            "# Enchantify — dream",
            "3 2 * * *",
            cd(f"{q(PYTHON)} scripts/dream.py", "logs/dream.log"),
            "scripts/dream.py",
        ),
        CronEntry(
            "# Enchantify — wallpaper",
            "0 7 * * *",
            cd(f"{q(PYTHON)} scripts/wallpaper.py --generate {q(player)}", "logs/wallpaper.log"),
            "scripts/wallpaper.py --generate",
        ),
        CronEntry(
            "# Enchantify — Sparky shinies",
            "0 8 * * *",
            cd(f"{q(PYTHON)} scripts/sparky.py", "logs/sparky.log"),
            "scripts/sparky.py",
        ),
        CronEntry(
            "# Enchantify — The Bleed",
            "0 18 * * *",
            cd(f"{q(PYTHON)} scripts/bleed.py", "logs/bleed.log"),
            "scripts/bleed.py",
        ),
        CronEntry(
            "# Enchantify — Gimble daily Actual sync",
            "20 16 * * *",
            cd(f"{q(PYTHON)} scripts/ledger-faculty.py daily-sync{send}", "logs/support-faculty.log"),
            "scripts/ledger-faculty.py daily-sync",
        ),
        CronEntry(
            "# Enchantify — Dr. Vellum daily brief",
            "35 7 * * *",
            cd(f"{q(PYTHON)} scripts/support-faculty.py vellum-brief", "logs/support-faculty.log"),
            "scripts/support-faculty.py vellum-brief",
        ),
        CronEntry(
            "# Enchantify — Dr. Inkrest morning check-in",
            "15 9 * * *",
            cd(f"{q(PYTHON)} scripts/support-faculty.py inkrest-checkin --slot morning", "logs/support-faculty.log"),
            "scripts/support-faculty.py inkrest-checkin --slot morning",
        ),
        CronEntry(
            "# Enchantify — Dr. Inkrest midday check-in",
            "15 13 * * *",
            cd(f"{q(PYTHON)} scripts/support-faculty.py inkrest-checkin --slot midday", "logs/support-faculty.log"),
            "scripts/support-faculty.py inkrest-checkin --slot midday",
        ),
        CronEntry(
            "# Enchantify — Dr. Inkrest evening check-in",
            "45 20 * * *",
            cd(f"{q(PYTHON)} scripts/support-faculty.py inkrest-checkin --slot evening", "logs/support-faculty.log"),
            "scripts/support-faculty.py inkrest-checkin --slot evening",
        ),
        CronEntry(
            "# Enchantify — support research: Vellum",
            "15 19 * * 2",
            cd(f"{q(PYTHON)} scripts/support-faculty.py research --doctor vellum{send}", "logs/support-faculty.log"),
            "scripts/support-faculty.py research --doctor vellum",
        ),
        CronEntry(
            "# Enchantify — support research: Inkrest",
            "15 19 * * 4",
            cd(f"{q(PYTHON)} scripts/support-faculty.py research --doctor inkrest{send}", "logs/support-faculty.log"),
            "scripts/support-faculty.py research --doctor inkrest",
        ),
        CronEntry(
            "# Enchantify — support guild: daily council meeting",
            "10 8 * * *",
            cd(f"{q(PYTHON)} scripts/support-guild.py daily{send}", "logs/support-faculty.log"),
            "scripts/support-guild.py daily",
        ),
        CronEntry(
            "# Enchantify — Bellkeeper morning Today Page",
            "20 8 * * *",
            cd(f"{q(PYTHON)} scripts/bellkeeper.py today {q(player)}{send}", "logs/support-faculty.log"),
            "scripts/bellkeeper.py today",
        ),
        CronEntry(
            "# Enchantify — Bellkeeper upcoming event preparation",
            "*/30 7-21 * * *",
            cd(f"{q(PYTHON)} scripts/bellkeeper.py upcoming {q(player)}{send}", "logs/support-faculty.log"),
            "scripts/bellkeeper.py upcoming",
        ),
        CronEntry(
            "# Enchantify — Bellkeeper evening scrap",
            "45 20 * * *",
            cd(f"{q(PYTHON)} scripts/bellkeeper.py evening {q(player)}{send}", "logs/support-faculty.log"),
            "scripts/bellkeeper.py evening",
        ),
        CronEntry(
            "# Enchantify — Bellkeeper week-ahead reading",
            "30 18 * * 0",
            cd(f"{q(PYTHON)} scripts/bellkeeper.py week {q(player)}{send}", "logs/support-faculty.log"),
            "scripts/bellkeeper.py week",
        ),
        CronEntry(
            "# Enchantify — Listening Desk market research",
            "5 13 * * *",
            cd(f"{q(PYTHON)} scripts/market-research.py daily{send}", "logs/publishing/market-research-cron.log"),
            "scripts/market-research.py daily",
        ),
        CronEntry(
            "# Enchantify — press abundance: Penny + Goldweaver daily council",
            "35 13 * * *",
            cd(f"{q(PYTHON)} scripts/press-abundance.py daily {q(player)}{send}", "logs/publishing/press-abundance-cron.log"),
            "scripts/press-abundance.py daily",
        ),
        CronEntry(
            "# Enchantify — The Book of You: nightly illustrated storybook PDF",
            "35 23 * * *",
            cd(f"{q(PYTHON)} scripts/storybook.py daily {q(player)}{send}", "logs/storybook.log"),
            "scripts/storybook.py daily",
        ),
        CronEntry(
            "# Enchantify — The Book of You: monthly collected volume",
            "55 23 28-31 * *",
            cd(
                f'[ "$(date -v+1d +\\%d)" = "01" ] && '
                f"{q(PYTHON)} scripts/storybook.py monthly {q(player)} --month $(date +\\%Y-\\%m){send}",
                "logs/storybook.log",
            ),
            "scripts/storybook.py monthly",
        ),
    ]
    if drawthings:
        rows.append(
            CronEntry(
                "# Enchantify — Draw Things hourly keepalive illustration",
                "7 * * * *",
                cd(f"{q(PYTHON)} scripts/drawthings-keepalive.py {drawthings_flags}", "logs/drawthings-keepalive.log"),
                "scripts/drawthings-keepalive.py",
            )
        )
    return rows


def install(player: str, *, dry_run: bool, telegram: bool, drawthings: bool) -> int:
    for path in [
        BASE / "logs",
        BASE / "logs" / "publishing",
        BASE / "logs" / "support-faculty",
        BASE / "logs" / "drawthings-keepalive",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    new_entries = entries(player, telegram=telegram, drawthings=drawthings)
    needles = [entry.needle for entry in new_entries]

    if dry_run:
        lines: list[str] = []
    else:
        current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        lines = current.stdout.splitlines() if current.returncode == 0 else []

    kept: list[str] = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if line.startswith("# Enchantify —"):
            skip_next = True
            continue
        if any(needle in line for needle in needles):
            continue
        if "/.openclaw/workspace/enchantify" in line and "/scripts/" in line:
            continue
        kept.append(line)

    if kept and kept[-1].strip():
        kept.append("")
    for entry in new_entries:
        kept.extend([entry.marker, entry.line(), ""])
    payload = "\n".join(kept).rstrip() + "\n"

    if dry_run:
        print(payload)
        return 0

    proc = subprocess.run(["crontab", "-"], input=payload, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        return proc.returncode
    print(f"Installed {len(new_entries)} Enchantify cron entries for player `{player}`.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Enchantify cron jobs")
    parser.add_argument("--player", default=os.environ.get("ENCHANTIFY_DEFAULT_PLAYER", "wanderer"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--no-drawthings", action="store_true")
    args = parser.parse_args()
    return install(
        args.player,
        dry_run=args.dry_run,
        telegram=not args.no_telegram,
        drawthings=not args.no_drawthings,
    )


if __name__ == "__main__":
    raise SystemExit(main())
