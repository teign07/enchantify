#!/usr/bin/env python3
"""
write-entity.py — Add or update an entity in lore/world-register.md.

Automatically places the entity in the correct section based on Belief score:
  15+   → Full Presence (table)
  5-14  → Fading Presence (table)
  <5    → Whisper Register (list)

Use --talisman to write to the Chapter Talismans section instead.
Use --gps-gated "Anchor Name" to mark a Location as an anchor room (GPS-gated).
Use --skill-lore "contract-id" to link an entity to a skill-lore contract (e.g. "obsidian", "github").
  The entity will decay if the contract goes inactive for 30+ days (handled by tick.py).

Usage:
  python3 scripts/write-entity.py "Name" Type Belief "Notes" [--talisman] [--gps-gated "Anchor"] [--skill-lore "id"] [--dry-run]

Examples:
  python3 scripts/write-entity.py "Zara Finch" NPC 25 "House guide, warm, knows more than she lets on"
  python3 scripts/write-entity.py "Boggle" NPC 4 "Last seen: dissolving into a jar of ink"
  python3 scripts/write-entity.py "Wind Cipher" Talisman 14 "Riddlewind — cowritten philosophy" --talisman
  python3 scripts/write-entity.py "The Harbor Lung" Location 12 "bj's REST anchor — tidal, breathing" --gps-gated "Harbor Lung"
  python3 scripts/write-entity.py "The Ink Well" AppEcho 8 "GitHub — the player's published thought" --skill-lore "github"
  python3 scripts/write-entity.py "Library Annex" AppEcho 12 "Obsidian vault — manuscripts and orphaned works" --skill-lore "obsidian"
"""
import re
import argparse
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
REGISTER = BASE_DIR / "lore" / "world-register.md"

FULL_HEADER     = "## Full Presence (Belief 15+)"
FADING_HEADER   = "## Fading Presence (Belief 5–14)"
WHISPER_HEADER  = "## Whisper Register (Belief <5)"
TALISMAN_HEADER = "## Chapter Talismans"


def remove_entity(text, name):
    """Remove all occurrences of an entity from every section and return the (cleaned_text, existing_type, existing_belief, existing_notes)."""
    existing_belief = 0
    existing_type = "NPC"
    existing_notes = ""
    
    # Table rows
    table_pattern = re.compile(r"^\|\s*" + re.escape(name) + r"\s*\|\s*([^\|]+)\s*\|\s*(\d+)\s*\|\s*([^\|]+)\s*\|[^\n]*\n", re.MULTILINE)
    match = table_pattern.search(text)
    if match:
        existing_type = match.group(1).strip()
        existing_belief = int(match.group(2))
        existing_notes = match.group(3).strip()
    text = table_pattern.sub("", text)
    
    # Whisper list items
    list_pattern = re.compile(r"^-\s+" + re.escape(name) + r"\s*\(([^,]+),\s*Belief\s*(\d+)\)\s*(?:—\s*(.*))?\n", re.MULTILINE)
    match = list_pattern.search(text)
    if match:
        existing_type = match.group(1).strip()
        existing_belief = int(match.group(2))
        existing_notes = match.group(3).strip() if match.group(3) else ""
    text = list_pattern.sub("", text)
    
    return text, existing_type, existing_belief, existing_notes


def insert_into_section(text, header, new_line):
    """Append a line to a section (before the next ## header or end of file)."""
    header_match = re.search(r"^" + re.escape(header) + r"\s*$", text, re.MULTILINE)
    if not header_match:
        # Section missing — append at end
        return text.rstrip() + f"\n\n{header}\n{new_line}\n"

    section_start = header_match.end()
    next_header = re.search(r"^\s*##\s", text[section_start:], re.MULTILINE)
    insert_pos = section_start + (next_header.start() if next_header else len(text[section_start:]))

    before = text[:insert_pos].rstrip()
    after  = text[insert_pos:].lstrip()
    return before + "\n" + new_line + "\n\n" + after


def main():
    parser = argparse.ArgumentParser(description="Add/update entity in world-register.md")
    parser.add_argument('name',   help='Entity name')
    parser.add_argument('type',   nargs='?', default='', help='Entity type (NPC, Object, Location, Talisman, ...)')
    parser.add_argument('belief', type=int, help='Belief score')
    parser.add_argument('notes',  nargs='?', default='', help='Notes / status line')
    parser.add_argument('--talisman', action='store_true',
                        help='Write to Chapter Talismans section')
    parser.add_argument('--gps-gated', metavar='ANCHOR',
                        help='Mark this Location as an anchor room — door only opens at the real-world anchor')
    parser.add_argument('--skill-lore', metavar='CONTRACT_ID',
                        help='Link this entity to a skill-lore contract (e.g. "obsidian", "github"). '
                             'Entity will decay if the contract is inactive for 30+ days.')
    parser.add_argument('--add', action='store_true',
                        help='Add the provided belief to the existing belief score instead of overwriting.')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.gps_gated:
        gated_tag = f"📍 GPS-gated: {args.gps_gated}"
        args.notes = f"{args.notes} | {gated_tag}" if args.notes else gated_tag

    if args.skill_lore:
        lore_tag = f"🔗 skill-lore:{args.skill_lore}"
        args.notes = f"{args.notes} | {lore_tag}" if args.notes else lore_tag

    if not REGISTER.exists():
        print(f"❌ {REGISTER} not found.")
        return

    text = REGISTER.read_text()
    text, existing_type, existing_belief, existing_notes = remove_entity(text, args.name)

    if not args.type:
        args.type = existing_type
    if not args.notes:
        args.notes = existing_notes

    if args.add:
        args.belief = existing_belief + args.belief

    if args.talisman:
        row = f"| {args.name} | {args.type} | {args.belief} | {args.notes} |"
        updated = insert_into_section(text, TALISMAN_HEADER, row)
    elif args.belief >= 15:
        row = f"| {args.name} | {args.type} | {args.belief} | {args.notes} |"
        updated = insert_into_section(text, FULL_HEADER, row)
    elif args.belief >= 5:
        row = f"| {args.name} | {args.type} | {args.belief} | {args.notes} |"
        updated = insert_into_section(text, FADING_HEADER, row)
    else:
        note_str = f" — {args.notes}" if args.notes else ""
        row = f"- {args.name} ({args.type}, Belief {args.belief}){note_str}"
        updated = insert_into_section(text, WHISPER_HEADER, row)

    if args.dry_run:
        section = (
            "Chapter Talismans" if args.talisman
            else "Full" if args.belief >= 15
            else "Fading" if args.belief >= 5
            else "Whisper"
        )
        lore_note = f" [skill-lore:{args.skill_lore}]" if args.skill_lore else ""
        print(f"[dry-run] Would place '{args.name}' in {section} Presence (Belief {args.belief}){lore_note}")
        return

    backup = REGISTER.with_suffix(".md.bak")
    shutil.copy2(REGISTER, backup)
    tmp = REGISTER.with_suffix(".md.tmp")
    tmp.write_text(updated if updated.endswith("\n") else updated + "\n")
    tmp.rename(REGISTER)

    print(f"✓ World register updated: {args.name} (Belief {args.belief})")
    print(f"  Backup: {backup.name}")


if __name__ == "__main__":
    main()
