#!/usr/bin/env python3
"""write-markdown.py — safely replace allowlisted markdown files.

Use this only for markdown pages that do not have a more specific writer.
Content is read from --file so agents do not write markdown directly.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

BASE = Path(__file__).parent.parent

ALLOWLIST = {
    BASE / "hooks" / "SPAWN-TEMPLATE.md",
    BASE / "lore" / "enchantments.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely replace an allowlisted markdown file")
    parser.add_argument("target", type=Path)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = args.target
    if not target.is_absolute():
        target = BASE / target
    target = target.resolve()

    allowed = {path.resolve() for path in ALLOWLIST}
    if target not in allowed:
        raise SystemExit(f"Refusing to write non-allowlisted markdown file: {target}")
    if not args.file.exists():
        raise SystemExit(f"Content file not found: {args.file}")

    content = args.file.read_text(encoding="utf-8")
    if not content.strip():
        raise SystemExit("Refusing to write empty markdown content")

    if args.dry_run:
        print(f"[dry-run] Would replace {target}")
        return 0

    if target.exists():
        backup = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup)

    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    tmp.rename(target)
    print(f"✓ Replaced {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
