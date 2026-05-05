#!/usr/bin/env python3
"""
write-school-life.py — Safely replace lore/school-life.md.

Never edit school-life.md directly. Use this script.
Content is read from --file (preferred) or stdin.

Usage:
  python3 scripts/write-school-life.py --file /tmp/enchantify-school-life.txt
"""

import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TARGET = BASE / "lore" / "school-life.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely replace school-life.md")
    parser.add_argument("--file", help="Path to content file (default: stdin)", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.file:
        src = Path(args.file)
        content = src.read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    if not content.strip():
        print("❌ No content provided. Pass --file or pipe via stdin.")
        raise SystemExit(1)

    if not content.startswith("# School Life at Enchantify Academy"):
        print("❌ Refusing to write: content does not look like school-life.md")
        raise SystemExit(1)

    if args.dry_run:
        print(f"[dry-run] Would replace {TARGET}")
        print(f"[dry-run] {len(content)} chars")
        return

    backup = TARGET.with_suffix(".md.bak")
    if TARGET.exists():
        backup.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
    TARGET.write_text(content, encoding="utf-8")
    print(f"✓ Replaced {TARGET}")
    print(f"  Backup: {backup}")


if __name__ == "__main__":
    main()
