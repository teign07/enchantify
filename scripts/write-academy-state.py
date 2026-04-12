#!/usr/bin/env python3
"""
write-academy-state.py — Replace lore/academy-state.md safely.

Never edit academy-state.md directly. Use this script.
Content is read from --file (preferred) or stdin.

The existing file is backed up to lore/academy-state.md.bak before writing.

Usage:
  python3 scripts/write-academy-state.py [--file /tmp/content.txt]
  python3 scripts/write-academy-state.py < /tmp/content.txt

Examples:
  python3 scripts/write-academy-state.py --file /tmp/enchantify-academy.txt
  echo "# Academy State..." | python3 scripts/write-academy-state.py
"""

import sys
import argparse
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "lore" / "academy-state.md"


def main():
    parser = argparse.ArgumentParser(description="Safely replace academy-state.md")
    parser.add_argument("--file", help="Path to content file (default: stdin)", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Read content
    if args.file:
        content_path = Path(args.file)
        if not content_path.exists():
            print(f"❌ Content file not found: {args.file}")
            sys.exit(1)
        new_content = content_path.read_text()
    else:
        new_content = sys.stdin.read()

    if not new_content.strip():
        print("❌ No content provided. Pass --file or pipe via stdin.")
        sys.exit(1)

    if args.dry_run:
        print(f"[dry-run] Would replace {STATE_FILE}")
        print(f"[dry-run] Content ({len(new_content)} chars, first 300):")
        print(new_content[:300] + ("..." if len(new_content) > 300 else ""))
        return

    # Backup existing file
    backup = STATE_FILE.with_suffix(".md.bak")
    if STATE_FILE.exists():
        shutil.copy2(STATE_FILE, backup)
        print(f"  Backup: {backup.name}")

    # Safe write: write to .tmp then rename (atomic on most filesystems)
    tmp = STATE_FILE.with_suffix(".md.tmp")
    tmp.write_text(new_content if new_content.endswith("\n") else new_content + "\n")
    tmp.rename(STATE_FILE)

    print(f"✓ Academy state updated: {STATE_FILE.name} ({len(new_content)} chars)")


if __name__ == "__main__":
    main()
