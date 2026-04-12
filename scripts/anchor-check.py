#!/usr/bin/env python3
"""
anchor-check.py [player] [lat] [lon] [--checkin] [--dry-run]

Checks which of the player's Anchors are within 200m of the given coordinates.
Prints nearby anchors in narrative-ready format for the Labyrinth.

With --checkin: if an anchor is within range, records the visit (updates
  last-visited date and adds +5 Belief to that anchor). This is the
  player physically arriving at a real-world anchor.

Usage:
  python3 scripts/anchor-check.py bj 44.4303 -69.0062
  python3 scripts/anchor-check.py bj 44.4303 -69.0062 --checkin
  python3 scripts/anchor-check.py bj 44.4303 -69.0062 --checkin --dry-run
"""

import re
import math
import shutil
import argparse
from pathlib import Path
from datetime import date

PROXIMITY_METERS = 200
CHECKIN_BELIEF   = 5
BASE_DIR = Path(__file__).parent.parent


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def parse_anchors(text):
    anchors = []
    sections = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        name = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""

        coords      = re.search(r"\*\*Coordinates:\*\*\s*([-\d.]+),\s*([-\d.]+)", body)
        anchor_type = re.search(r"\*\*Type:\*\*\s*(\w+)", body)
        belief      = re.search(r"\*\*Belief invested:\*\*\s*(\d+)", body)
        echo        = re.search(r"\*\*Academy echo:\*\*\s*(.+)", body)
        words       = re.search(r"\*\*Player's words:\*\*\s*\"(.+)\"", body)
        last_visit  = re.search(r"\*\*Last visited:\*\*\s*(\d{4}-\d{2}-\d{2})", body)

        if not coords:
            continue

        anchors.append({
            "name":        name,
            "lat":         float(coords.group(1)),
            "lon":         float(coords.group(2)),
            "type":        anchor_type.group(1) if anchor_type else "UNKNOWN",
            "belief":      int(belief.group(1)) if belief else 0,
            "echo":        echo.group(1).strip() if echo else "",
            "words":       words.group(1).strip() if words else "",
            "last_visited": last_visit.group(1) if last_visit else None,
        })
    return anchors


def checkin_anchor(anchor_file_path, anchor_name, dry_run=False):
    """
    Record a check-in: update last-visited and increment Belief by CHECKIN_BELIEF.
    Returns (old_belief, new_belief).
    """
    text = anchor_file_path.read_text()
    today = date.today().isoformat()

    # Find the anchor's section
    section_re = re.compile(
        r"(^## " + re.escape(anchor_name) + r"\s*$)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL
    )
    m = section_re.search(text)
    if not m:
        print(f"  ⚠ Could not locate anchor section '{anchor_name}' for check-in.")
        return None, None

    section_body = m.group(2)

    # Get current Belief
    belief_match = re.search(r"(\*\*Belief invested:\*\*\s*)(\d+)", section_body)
    if not belief_match:
        print(f"  ⚠ No Belief field found in anchor '{anchor_name}'.")
        return None, None

    old_belief = int(belief_match.group(2))
    new_belief = old_belief + CHECKIN_BELIEF

    # Update Belief
    new_section = section_body.replace(
        belief_match.group(0),
        belief_match.group(1) + str(new_belief)
    )

    # Update or add Last visited
    last_re = re.search(r"\*\*Last visited:\*\*\s*\d{4}-\d{2}-\d{2}", new_section)
    if last_re:
        new_section = new_section.replace(last_re.group(0), f"**Last visited:** {today}")
    else:
        # Insert after Belief line
        new_section = re.sub(
            r"(\*\*Belief invested:\*\*\s*\d+)",
            rf"\1\n**Last visited:** {today}",
            new_section
        )

    new_text = text[:m.start(2)] + new_section + text[m.end(2):]

    if dry_run:
        print(f"  [dry-run] Would update '{anchor_name}': Belief {old_belief} → {new_belief}, last-visited → {today}")
        return old_belief, new_belief

    backup = anchor_file_path.with_suffix(".md.bak")
    shutil.copy2(anchor_file_path, backup)
    tmp = anchor_file_path.with_suffix(".md.tmp")
    tmp.write_text(new_text if new_text.endswith("\n") else new_text + "\n")
    tmp.rename(anchor_file_path)

    return old_belief, new_belief


def main():
    parser = argparse.ArgumentParser(description="Check anchor proximity and optionally record a check-in")
    parser.add_argument("player")
    parser.add_argument("lat", type=float)
    parser.add_argument("lon", type=float)
    parser.add_argument("--checkin", action="store_true",
                        help="Record a visit: update last-visited and grow anchor Belief (+5)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    anchor_file = BASE_DIR / "players" / f"{args.player}-anchors.md"
    if not anchor_file.exists():
        print(f"No anchor file found for player '{args.player}'.")
        return

    text = anchor_file.read_text()
    anchors = parse_anchors(text)

    if not anchors:
        print("No anchors defined yet.")
        return

    nearby = []
    for anchor in anchors:
        dist = haversine(args.lat, args.lon, anchor["lat"], anchor["lon"])
        if dist <= PROXIMITY_METERS:
            nearby.append((anchor, dist))

    if not nearby:
        nearest = min(anchors, key=lambda a: haversine(args.lat, args.lon, a["lat"], a["lon"]))
        nearest_dist = haversine(args.lat, args.lon, nearest["lat"], nearest["lon"])
        print(f"No anchors nearby. Nearest: {nearest['name']} [{nearest['type']}] — {nearest_dist:.0f}m away.")
        return

    print(f"CHECK-IN — NEARBY ({len(nearby)}):")
    for anchor, dist in sorted(nearby, key=lambda x: x[1]):
        print(f"\n  {anchor['name']} [{anchor['type']}] — {dist:.0f}m")
        if anchor["words"]:
            print(f"  \"{anchor['words']}\"")
        if anchor["echo"]:
            print(f"  Academy echo: {anchor['echo']}")
        if anchor["last_visited"]:
            print(f"  Last visited: {anchor['last_visited']}")

        if args.checkin:
            old_b, new_b = checkin_anchor(anchor_file, anchor["name"], dry_run=args.dry_run)
            if old_b is not None:
                print(f"  ✓ Belief: {old_b} → {new_b}  (visited today)")


if __name__ == "__main__":
    main()
