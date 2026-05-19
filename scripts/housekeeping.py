#!/usr/bin/env python3
"""Nightly storage housekeeping for Enchantify/OpenClaw.

Conservative by design:
- keep the newest OpenClaw dated backups
- trim transient scene outbox files
- trim old temporary markdown/script helper backups
- never touch model files, Draw Things, Bleed issues, diaries, letters, or logs
  unless explicitly added later.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
sys.path.insert(0, str(SCRIPTS))
import cron_steward  # type: ignore

OPENCLAW = Path.home() / ".openclaw"
BACKUPS = OPENCLAW / "backups"
SCENE_OUTBOX = BASE / "tmp" / "scene-outbox"
LOG_DIR = BASE / "logs" / "housekeeping"


def size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() or child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def human(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{num}B"


def remove_path(path: Path, *, dry_run: bool) -> int:
    freed = size_bytes(path)
    if dry_run:
        return freed
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)
    return freed


def dated_backup_dirs() -> list[Path]:
    if not BACKUPS.exists():
        return []
    dirs = [
        path for path in BACKUPS.iterdir()
        if path.is_dir() and len(path.name) == 10 and path.name[:4].isdigit()
    ]
    return sorted(dirs, key=lambda p: p.name)


def prune_openclaw_backups(*, keep: int, dry_run: bool) -> list[dict]:
    backups = dated_backup_dirs()
    victims = backups[:-keep] if keep > 0 else backups
    removed: list[dict] = []
    for path in victims:
        freed = remove_path(path, dry_run=dry_run)
        removed.append({"path": str(path), "bytes": freed, "size": human(freed)})
    log = BACKUPS / "backup.log"
    if log.exists() and log.stat().st_size > 25 * 1024 * 1024:
        freed = remove_path(log, dry_run=dry_run)
        removed.append({"path": str(log), "bytes": freed, "size": human(freed)})
    return removed


def files_older_than(root: Path, *, days: int) -> Iterable[Path]:
    if not root.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    out: list[Path] = []
    for path in root.rglob("*"):
        try:
            if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                out.append(path)
        except OSError:
            continue
    return out


def prune_files(root: Path, *, days: int, dry_run: bool) -> list[dict]:
    removed: list[dict] = []
    for path in files_older_than(root, days=days):
        freed = remove_path(path, dry_run=dry_run)
        removed.append({"path": str(path), "bytes": freed, "size": human(freed)})
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservative nightly storage cleanup.")
    parser.add_argument("--keep-openclaw-backups", type=int, default=3)
    parser.add_argument("--scene-outbox-days", type=int, default=2)
    parser.add_argument("--tmp-backup-days", type=int, default=14)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with cron_steward.run("housekeeping", dry_run=args.dry_run) as ctx:
        removed: list[dict] = []
        removed.extend(prune_openclaw_backups(keep=max(0, args.keep_openclaw_backups), dry_run=args.dry_run))
        removed.extend(prune_files(SCENE_OUTBOX, days=args.scene_outbox_days, dry_run=args.dry_run))
        for root in (
            Path("/tmp/enchantify-agent-backups"),
            Path("/tmp/enchantify-markdown-backups"),
            Path("/tmp/enchantify-vellum-backups"),
            Path("/tmp/enchantify-therapy-backups"),
        ):
            removed.extend(prune_files(root, days=args.tmp_backup_days, dry_run=args.dry_run))

        total = sum(item["bytes"] for item in removed)
        report = {
            "at": datetime.now().isoformat(timespec="seconds"),
            "dry_run": args.dry_run,
            "removed_count": len(removed),
            "freed_bytes": total,
            "freed": human(total),
            "kept_openclaw_backups": [str(path) for path in dated_backup_dirs()[-max(0, args.keep_openclaw_backups):]],
            "removed": removed,
        }
        ctx["removed_count"] = len(removed)
        ctx["freed"] = human(total)
        if not args.dry_run:
            (LOG_DIR / "last-run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            action = "Would free" if args.dry_run else "Freed"
            print(f"{action} {human(total)} across {len(removed)} item(s).")
            for item in removed[:20]:
                print(f"- {item['size']} {item['path']}")
            if len(removed) > 20:
                print(f"... {len(removed) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
