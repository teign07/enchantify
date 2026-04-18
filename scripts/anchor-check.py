#!/usr/bin/env python3
"""
anchor-check.py [player] [lat] [lon] [--checkin] [--dry-run]

Checks which of the player's Anchors are within 200m of the given coordinates.
Prints nearby anchors in narrative-ready format for the Labyrinth.

With --checkin: records the visit (updates last-visited, visit count, and grows
  anchor Belief +5), then outputs OUTER_STACKS_MODE directive telling the
  Labyrinth whether this is a first visit (generate the room) or a return visit
  (evolve and enter the room).

Usage:
  python3 scripts/anchor-check.py bj 44.4303 -69.0062
  python3 scripts/anchor-check.py bj 44.4303 -69.0062 --checkin
  python3 scripts/anchor-check.py bj 44.4303 -69.0062 --checkin --dry-run
"""

import re
import math
import shutil
import argparse
import importlib.util
from pathlib import Path
from datetime import date, datetime


def _load_pocket_anchor():
    spec = importlib.util.spec_from_file_location(
        "pocket_anchor", Path(__file__).parent / "pocket-anchor.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

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

        coords       = re.search(r"\*\*Coordinates:\*\*\s*([-\d.]+),\s*([-\d.]+)", body)
        anchor_type  = re.search(r"\*\*Type:\*\*\s*(\w+)", body)
        belief       = re.search(r"\*\*Belief invested:\*\*\s*(\d+)", body)
        echo         = re.search(r"\*\*Academy echo:\*\*\s*(.+)", body)
        words        = re.search(r"\*\*Player's words:\*\*\s*\"(.+)\"", body)
        last_visit   = re.search(r"\*\*Last visited:\*\*\s*(\d{4}-\d{2}-\d{2})", body)
        visit_count  = re.search(r"\*\*Visit count:\*\*\s*(\d+)", body)
        season       = re.search(r"\*\*Season:\*\*\s*([^\n]+)", body)
        outer_room   = re.search(r"\*\*Outer Stacks room:\*\*\s*([^\n]+)", body)
        local_rule   = re.search(r"\*\*Local rule:\*\*\s*([^\n]+)", body)

        if not coords:
            continue

        outer_room_val = outer_room.group(1).strip() if outer_room else ""
        # Treat placeholder text as not-yet-generated
        if outer_room_val.startswith("*(not yet") or outer_room_val.startswith("*(set at"):
            outer_room_val = ""

        local_rule_val = local_rule.group(1).strip() if local_rule else ""
        if local_rule_val.startswith("*(set at"):
            local_rule_val = ""

        anchors.append({
            "name":         name,
            "lat":          float(coords.group(1)),
            "lon":          float(coords.group(2)),
            "type":         anchor_type.group(1) if anchor_type else "UNKNOWN",
            "belief":       int(belief.group(1)) if belief else 0,
            "echo":         echo.group(1).strip() if echo else "",
            "words":        words.group(1).strip() if words else "",
            "last_visited": last_visit.group(1) if last_visit else None,
            "visit_count":  int(visit_count.group(1)) if visit_count else 0,
            "season":       season.group(1).strip() if season else "",
            "outer_room":   outer_room_val,
            "local_rule":   local_rule_val,
        })
    return anchors


def get_current_season():
    """Return the current season name based on month."""
    m = date.today().month
    if m in (3, 4):
        return "Mud Season (The Thaw)"
    elif m in (5, 6, 7, 8):
        return "Gold Season (Summer)"
    elif m in (9, 10):
        return "Stick Season (The Bare)"
    else:
        return "Deep Winter"


def checkin_anchor(anchor_file_path, anchor_name, dry_run=False):
    """
    Record a check-in: update last-visited, increment visit count, grow Belief.
    Returns dict with old/new Belief and new visit count.
    """
    text = anchor_file_path.read_text()
    today = date.today().isoformat()

    section_re = re.compile(
        r"(^## " + re.escape(anchor_name) + r"\s*$)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL
    )
    m = section_re.search(text)
    if not m:
        print(f"  ⚠ Could not locate anchor section '{anchor_name}' for check-in.")
        return None

    section_body = m.group(2)

    # Belief
    belief_match = re.search(r"(\*\*Belief invested:\*\*\s*)(\d+)", section_body)
    if not belief_match:
        print(f"  ⚠ No Belief field found in anchor '{anchor_name}'.")
        return None

    old_belief = int(belief_match.group(2))
    new_belief = old_belief + CHECKIN_BELIEF
    new_section = section_body.replace(
        belief_match.group(0),
        belief_match.group(1) + str(new_belief)
    )

    # Visit count
    vc_match = re.search(r"(\*\*Visit count:\*\*\s*)(\d+)", new_section)
    if vc_match:
        old_count = int(vc_match.group(2))
        new_count = old_count + 1
        new_section = new_section.replace(
            vc_match.group(0),
            vc_match.group(1) + str(new_count)
        )
    else:
        new_count = 1
        new_section = re.sub(
            r"(\*\*Belief invested:\*\*\s*\d+)",
            rf"\1\n- **Visit count:** {new_count}",
            new_section
        )

    # Last visited
    last_re = re.search(r"\*\*Last visited:\*\*\s*[\w*()\-]+", new_section)
    if last_re:
        new_section = new_section.replace(last_re.group(0), f"**Last visited:** {today}")
    else:
        new_section = re.sub(
            r"(\*\*Visit count:\*\*\s*\d+)",
            rf"\1\n- **Last visited:** {today}",
            new_section
        )

    new_text = text[:m.start(2)] + new_section + text[m.end(2):]

    if dry_run:
        print(f"  [dry-run] '{anchor_name}': Belief {old_belief}→{new_belief}, visit #{new_count}, last-visited→{today}")
        return {"old_belief": old_belief, "new_belief": new_belief, "visit_count": new_count}

    backup = anchor_file_path.with_suffix(".md.bak")
    shutil.copy2(anchor_file_path, backup)
    tmp = anchor_file_path.with_suffix(".md.tmp")
    tmp.write_text(new_text if new_text.endswith("\n") else new_text + "\n")
    tmp.rename(anchor_file_path)

    return {"old_belief": old_belief, "new_belief": new_belief, "visit_count": new_count}


def print_outer_stacks_directive(anchor, visit_count, current_season):
    """
    Print the OUTER_STACKS_MODE directive for the Labyrinth.
    first visit = no room yet → GENERATE
    return visit = room exists → ENTER with evolution context
    """
    print()
    print("--- OUTER STACKS ---")
    print(f"ANCHOR: {anchor['name']}  [{anchor['type']}]")
    print(f"PLAYER_WORDS: \"{anchor['words']}\"")
    print(f"CREATION_SEASON: {anchor['season']}")
    print(f"CURRENT_SEASON: {current_season}")

    if not anchor["outer_room"]:
        # First real-world visit — room not yet generated
        print(f"OUTER_STACKS_MODE: FIRST_VISIT")
        print()
        print("GENERATE: This is the player's first real arrival. Generate the Outer Stacks")
        print("  room now. Read lore/outer-stacks.md → Room Archetypes. Choose based on:")
        print(f"  anchor type ({anchor['type']}), player's words, creation season vs. current")
        print(f"  season, current Belief. Add a local rule if the room calls for one.")
        print("  Narrate the door opening and the room in full. Do not rush.")
        print("  After narrating, write the room to players/[name]-anchors.md:")
        print("    **Outer Stacks room:** [one-paragraph description]")
        print("    **Local rule:** [rule or 'none']")
        print("  Then update update-player.py for Belief growth from the visit.")
    else:
        # Return visit
        print(f"OUTER_STACKS_MODE: RETURN_VISIT  (visit #{visit_count})")
        print()
        print(f"ROOM: {anchor['outer_room']}")
        if anchor["local_rule"] and anchor["local_rule"].lower() != "none":
            print(f"LOCAL_RULE: {anchor['local_rule']}  ← takes effect immediately on entry")

        # Season delta
        if anchor["season"] and anchor["season"] != current_season:
            print(f"SEASON_SHIFT: room was born in {anchor['season']}, now it is {current_season}")
            print("  → adjust inhabitant mood and room atmosphere accordingly (see outer-stacks.md Seasonal Effects)")

        # Visit count milestone hints
        if visit_count == 3:
            print("EVOLUTION: 3rd visit — inhabitants are calibrating. First sign of recognition.")
        elif visit_count == 7:
            print("EVOLUTION: 7th visit — the room has a relationship with the player now.")
        elif visit_count == 12:
            print("EVOLUTION: 12th visit — the room knows them. A second, deeper door may appear.")
        elif visit_count > 1:
            print(f"EVOLUTION: visit #{visit_count} — let inhabitants show cumulative memory.")

        if anchor["echo"]:
            print(f"INSIDE_ECHO: {anchor['echo']}  (still active in the Academy)")

    print("--------------------")
    print()


def print_pocket_directive(anchor: dict, session: dict, current_season: str):
    """Print the OUTER_STACKS_MODE directive for a pocket anchor visit."""
    expires = datetime.fromisoformat(session["expires_at"])
    remaining = int((expires - datetime.now()).total_seconds() / 60)

    print()
    print("--- OUTER STACKS (POCKET) ---")
    print(f"ANCHOR: {anchor['name']}  [{anchor['type']}]")
    print(f"ACCESS: pocket anchor — calling card from the Goblin Index Empire")
    print(f"WINDOW: {remaining} min remaining  (closes {expires.strftime('%H:%M')})")
    print(f"PLAYER_WORDS: \"{anchor['words']}\"")
    print(f"CURRENT_SEASON: {current_season}")

    if not anchor["outer_room"]:
        print("OUTER_STACKS_MODE: POCKET_FIRST")
        print()
        print("NOTE: The player has not physically visited this anchor yet.")
        print("  The room is heard, not seen — narrate sounds and edges only.")
        print("  The door is ajar. They cannot fully enter. Not yet.")
    else:
        print(f"OUTER_STACKS_MODE: POCKET_RETURN  (visit #{anchor['visit_count']})")
        print()
        print(f"ROOM: {anchor['outer_room']}")
        if anchor["local_rule"] and anchor["local_rule"].lower() != "none":
            print(f"LOCAL_RULE: {anchor['local_rule']}  ← still in effect")
        if anchor["season"] and anchor["season"] != current_season:
            print(f"SEASON_SHIFT: room was born in {anchor['season']}, now it is {current_season}")
            print("  → adjust atmosphere accordingly; the room is seen from a distance")
        if anchor["echo"]:
            print(f"INSIDE_ECHO: {anchor['echo']}")
        print()
        print("POCKET_NOTE: The connection is real but thin. The room is present.")
        print("  Inhabitants know the player is not physically there — they speak")
        print("  with slight formality, as if through glass. When the window closes,")
        print("  the room fades mid-sentence. Do not let the player forget the clock.")

    print("--------------------")
    print()


def main():
    parser = argparse.ArgumentParser(description="Check anchor proximity — Outer Stacks gateway")
    parser.add_argument("player")
    parser.add_argument("lat", type=float, nargs="?", default=None)
    parser.add_argument("lon", type=float, nargs="?", default=None)
    parser.add_argument("--checkin", action="store_true",
                        help="Record visit + output Outer Stacks entry directive")
    parser.add_argument("--pocket", metavar="ANCHOR",
                        help="Enter via pocket anchor session (no GPS needed)")
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

    current_season = get_current_season()

    # ── Pocket anchor path ────────────────────────────────────────────────────
    if args.pocket:
        pa = _load_pocket_anchor()
        session = pa.check_active(args.player, args.pocket)
        if not session:
            print(f"No active pocket anchor session for '{args.pocket}'.")
            print(f"  Activate one with: python3 scripts/pocket-anchor.py activate {args.player} \"{args.pocket}\"")
            return
        match = next((a for a in anchors if session["anchor_name"].lower() in a["name"].lower()
                      or a["name"].lower() in session["anchor_name"].lower()), None)
        if not match:
            print(f"Anchor '{session['anchor_name']}' not found in anchor file.")
            return
        print_pocket_directive(match, session, current_season)
        return

    # ── Normal GPS path ───────────────────────────────────────────────────────
    if args.lat is None or args.lon is None:
        parser.error("lat and lon are required unless using --pocket")

    nearby = []
    for anchor in anchors:
        dist = haversine(args.lat, args.lon, anchor["lat"], anchor["lon"])
        if dist <= PROXIMITY_METERS:
            nearby.append((anchor, dist))

    if not nearby:
        # Check if a pocket session is active for any anchor — hint if so
        try:
            pa = _load_pocket_anchor()
            pa.cmd_expire(args.player)
            state = pa.load_state()
            ps = pa.get_player_state(state, args.player)
            active = [(name, pa.active_session(ast)) for name, ast in ps.items()
                      if isinstance(ast, dict) and pa.active_session(ast)]
            if active:
                name, sess = active[0]
                expires = datetime.fromisoformat(sess["expires_at"])
                remaining = int((expires - datetime.now()).total_seconds() / 60)
                print(f"Not at anchor. Pocket session active: '{name}' ({remaining} min remaining).")
                print(f"  Enter with: python3 scripts/anchor-check.py {args.player} --pocket \"{name}\"")
                return
        except Exception:
            pass

        nearest = min(anchors, key=lambda a: haversine(args.lat, args.lon, a["lat"], a["lon"]))
        nearest_dist = haversine(args.lat, args.lon, nearest["lat"], nearest["lon"])
        print(f"No anchors nearby. Nearest: {nearest['name']} [{nearest['type']}] — {nearest_dist:.0f}m away.")
        print("The door is sealed. It is visible in the corridor. Light comes from under it.")
        return

    print(f"ANCHOR PROXIMITY — {len(nearby)} nearby:")
    for anchor, dist in sorted(nearby, key=lambda x: x[1]):
        visit_count = anchor["visit_count"]

        print(f"\n  {anchor['name']} [{anchor['type']}] — {dist:.0f}m")
        if anchor["words"]:
            print(f"  \"{anchor['words']}\"")
        if anchor["echo"]:
            print(f"  Academy echo: {anchor['echo']}")
        room_status = "generated" if anchor["outer_room"] else "not yet visited"
        print(f"  Outer Stacks room: {room_status}  ·  Visits: {visit_count}")
        if anchor["last_visited"]:
            print(f"  Last visited: {anchor['last_visited']}")

        if args.checkin:
            result = checkin_anchor(anchor_file, anchor["name"], dry_run=args.dry_run)
            if result:
                new_count = result["visit_count"]
                print(f"  ✓ Belief: {result['old_belief']} → {result['new_belief']}  ·  Visit #{new_count}")
                anchor["visit_count"] = new_count
                print_outer_stacks_directive(anchor, new_count, current_season)


if __name__ == "__main__":
    main()
