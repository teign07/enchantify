#!/usr/bin/env python3
"""
write-capabilities.py — Safely replace hooks/enchantify-capabilities.md.

Never edit the capabilities document directly. Use this script.
Content is read from --file (preferred) or stdin.
"""

import sys
import argparse
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TARGET = BASE_DIR / "hooks" / "enchantify-capabilities.md"


def main():
    parser = argparse.ArgumentParser(description="Safely replace enchantify-capabilities.md")
    parser.add_argument("--file", help="Path to content file (default: stdin)", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.file:
        content_path = Path(args.file)
        if not content_path.exists():
            print(f"❌ Content file not found: {args.file}")
            sys.exit(1)
        new_content = content_path.read_text(encoding="utf-8")
    else:
        new_content = sys.stdin.read()

    if not new_content.strip():
        print("❌ No content provided. Pass --file or pipe via stdin.")
        sys.exit(1)

    if args.dry_run:
        print(f"[dry-run] Would replace {TARGET}")
        print(new_content[:300] + ("..." if len(new_content) > 300 else ""))
        return

    if TARGET.exists():
        backup_dir = Path("/tmp/enchantify-markdown-backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"{TARGET.name}.bak"
        shutil.copy2(TARGET, backup)
        print(f"  Backup: {backup}")

    tmp = TARGET.with_suffix(".md.tmp")
    tmp.write_text(new_content if new_content.endswith("\n") else new_content + "\n", encoding="utf-8")
    tmp.rename(TARGET)
    print(f"✓ Capabilities updated: {TARGET.name} ({len(new_content)} chars)")


if __name__ == "__main__":
    main()
