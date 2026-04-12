#!/usr/bin/env python3
"""
write-diary.py — Write the Labyrinth's session diary safely.

Never write memory/diary/[date].md directly. Use this script.
Content is read from --file (preferred) or stdin.

Usage:
  python3 scripts/write-diary.py [player] [--date YYYY-MM-DD] [--file /tmp/diary.txt]
  python3 scripts/write-diary.py [player] < /tmp/diary.txt

Examples:
  python3 scripts/write-diary.py bj --file /tmp/enchantify-diary.txt
  python3 scripts/write-diary.py bj --date 2026-04-08 --file /tmp/enchantify-diary.txt

If a diary file already exists for today, the new content is appended
with a session separator (multiple sessions in one day are valid).
"""

import sys
import os
import argparse
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DIARY_DIR = BASE_DIR / "memory" / "diary"


def main():
    parser = argparse.ArgumentParser(description="Write Labyrinth diary entry")
    parser.add_argument("player", help="Player name")
    parser.add_argument("--date", help="Date override (YYYY-MM-DD)", default=None)
    parser.add_argument("--file", help="Path to content file (default: stdin)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written without writing")
    args = parser.parse_args()

    # Determine date
    entry_date = args.date if args.date else date.today().isoformat()

    # Read content
    if args.file:
        content_path = Path(args.file)
        if not content_path.exists():
            print(f"❌ Content file not found: {args.file}")
            sys.exit(1)
        content = content_path.read_text().strip()
    else:
        content = sys.stdin.read().strip()

    if not content:
        print("❌ No content provided. Pass --file or pipe content via stdin.")
        sys.exit(1)

    # Determine output path
    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIARY_DIR / f"{entry_date}.md"

    if args.dry_run:
        print(f"[dry-run] Would write diary to: {out_path}")
        print(f"[dry-run] Content ({len(content)} chars):")
        print(content[:300] + ("..." if len(content) > 300 else ""))
        return

    if out_path.exists():
        # Append with session separator
        existing = out_path.read_text()
        session_num = existing.count("---\n\n## Session") + 2
        separator = f"\n\n---\n\n## Session {session_num}\n\n"
        out_path.write_text(existing.rstrip() + separator + content + "\n")
        print(f"✓ Appended session {session_num} to diary: {out_path}")
    else:
        header = f"# Labyrinth Diary — {entry_date}\n*Player: {args.player}*\n\n## Session 1\n\n"
        out_path.write_text(header + content + "\n")
        print(f"✓ Diary written: {out_path}")


if __name__ == "__main__":
    main()
