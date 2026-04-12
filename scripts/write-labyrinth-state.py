#!/usr/bin/env python3
"""
write-labyrinth-state.py — Update a named section of memory/labyrinth-state.md safely.

Never edit labyrinth-state.md directly. Use this script.
Content is read from --file (preferred) or stdin.

Sections:
  register    → ## Current Register
  watching    → ## What It's Watching
  assessment  → ## Hidden Assessment
  nothing     → ## The Nothing's Pressure
  notes       → ## Notes to Self

Usage:
  python3 scripts/write-labyrinth-state.py [section] [--file /tmp/content.txt]
  python3 scripts/write-labyrinth-state.py [section] < /tmp/content.txt

Examples:
  python3 scripts/write-labyrinth-state.py nothing --file /tmp/enchantify-state.txt
  python3 scripts/write-labyrinth-state.py notes --file /tmp/enchantify-notes.txt
"""

import sys
import re
import argparse
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "memory" / "labyrinth-state.md"

SECTIONS = {
    "register":   "## Current Register",
    "watching":   "## What It's Watching",
    "assessment": "## Hidden Assessment",
    "nothing":    "## The Nothing's Pressure",
    "notes":      "## Notes to Self",
}


def replace_section(text: str, header: str, new_content: str) -> str:
    """Replace the content of a section, preserving all other sections."""
    # Find the section header
    header_pattern = re.compile(r"^" + re.escape(header) + r"\s*$", re.MULTILINE)
    match = header_pattern.search(text)
    if not match:
        # Section not found — append it
        return text.rstrip() + f"\n\n{header}\n\n{new_content}\n"

    section_start = match.end()

    # Find the next ## header (or end of file)
    next_header = re.search(r"^\s*##\s", text[section_start:], re.MULTILINE)
    if next_header:
        section_end = section_start + next_header.start()
    else:
        section_end = len(text)

    return (
        text[:section_start]
        + "\n\n"
        + new_content.strip()
        + "\n\n"
        + text[section_end:].lstrip()
    )


def main():
    parser = argparse.ArgumentParser(description="Update a section of labyrinth-state.md")
    parser.add_argument("section", choices=list(SECTIONS.keys()),
                        help="Section to update")
    parser.add_argument("--file", help="Path to content file (default: stdin)", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Read content
    if args.file:
        content_path = Path(args.file)
        if not content_path.exists():
            print(f"❌ Content file not found: {args.file}")
            sys.exit(1)
        new_content = content_path.read_text().strip()
    else:
        new_content = sys.stdin.read().strip()

    if not new_content:
        print("❌ No content provided. Pass --file or pipe via stdin.")
        sys.exit(1)

    header = SECTIONS[args.section]

    # Read current state (create if missing)
    if STATE_FILE.exists():
        current = STATE_FILE.read_text()
    else:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        current = f"# The Labyrinth's Inner State\n\n*A living document. Updated at each session close.*\n*This is the Labyrinth's private self — not shown to the player.*\n\n"
        for h in SECTIONS.values():
            current += f"{h}\n\n*(Not yet written.)*\n\n"

    updated = replace_section(current, header, new_content)

    if args.dry_run:
        print(f"[dry-run] Would update section '{args.section}' in {STATE_FILE}")
        print(f"[dry-run] New content:\n{new_content[:200]}{'...' if len(new_content) > 200 else ''}")
        return

    # Safe write: backup then replace
    backup = STATE_FILE.with_suffix(".md.bak")
    if STATE_FILE.exists():
        shutil.copy2(STATE_FILE, backup)

    tmp = STATE_FILE.with_suffix(".md.tmp")
    tmp.write_text(updated)
    tmp.rename(STATE_FILE)

    print(f"✓ Updated '{args.section}' in {STATE_FILE.name}")
    if backup.exists():
        print(f"  Backup: {backup.name}")


if __name__ == "__main__":
    main()
