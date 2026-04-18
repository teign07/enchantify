#!/usr/bin/env python3
"""
pocket-anchor.py — Remote access to anchored Outer Stacks rooms.

Once you've physically visited an anchor, it knows you. Every new moon
the Goblin Index Empire delivers a calling card — one charge per anchor
you've visited, letting you open a 30-minute window to that place from
wherever you are.

Commands:
  activate <player> <anchor_name>   Spend a charge, open a 30-min session
  status   <player>                 Show charges and active sessions
  refill   <player>                 Issue monthly charges (run by tick.py on new moon)
  expire   <player>                 Clear any expired sessions (run at session start)

Usage:
  python3 scripts/pocket-anchor.py activate bj "Belfast Co-Op"
  python3 scripts/pocket-anchor.py status bj
  python3 scripts/pocket-anchor.py refill bj
  python3 scripts/pocket-anchor.py refill bj --dry-run
"""

import json
import argparse
import re
import math
from pathlib import Path
from datetime import datetime, timedelta, date

BASE_DIR    = Path(__file__).parent.parent
STATE_FILE  = BASE_DIR / "config" / "pocket-anchors.json"
ANCHORS_DIR = BASE_DIR / "players"

WINDOW_MINUTES = 30
REFILL_DAY     = 1   # day-of-month to treat as "new moon" for refill


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def get_player_state(state: dict, player: str) -> dict:
    return state.setdefault(player, {})


def visited_anchors(player: str) -> list[str]:
    """Return all defined anchor names for a player. Having a defined anchor means
    you were physically there to create it — visit count may be 0 if pre-dates the
    check-in script."""
    anchor_file = ANCHORS_DIR / f"{player}-anchors.md"
    if not anchor_file.exists():
        return []
    text = anchor_file.read_text()
    # Any ## section with a Coordinates field is a real anchor
    names = re.findall(r"^## (.+)$", text, re.MULTILINE)
    result = []
    for name in names:
        if re.search(r"\*\*Coordinates:\*\*", text[text.find(f"## {name}"):]):
            result.append(name)
    return result


def active_session(anchor_state: dict):
    """Return active session dict if within window, else None."""
    session = anchor_state.get("active_session")
    if not session:
        return None
    expires = datetime.fromisoformat(session["expires_at"])
    if datetime.now() < expires:
        return session
    return None


def cmd_activate(player: str, anchor_name: str, dry_run: bool = False):
    state = load_state()
    ps    = get_player_state(state, player)

    # Resolve partial anchor name
    visited = visited_anchors(player)
    matches = [a for a in visited if anchor_name.lower() in a.lower()]
    if not matches:
        all_visited = visited_anchors(player)
        if not all_visited:
            print(f"✗ {player} has no physically-visited anchors yet.")
        else:
            print(f"✗ No visited anchor matching '{anchor_name}'.")
            print(f"  Known anchors: {', '.join(all_visited)}")
        return
    anchor_name = matches[0]

    anchor_state = ps.setdefault(anchor_name, {"charges": 0, "last_refill": None})

    # Check for already-active session
    sess = active_session(anchor_state)
    if sess:
        expires = datetime.fromisoformat(sess["expires_at"])
        remaining = int((expires - datetime.now()).total_seconds() / 60)
        print(f"✓ Session already active for '{anchor_name}' — {remaining} min remaining.")
        return

    if anchor_state.get("charges", 0) < 1:
        last = anchor_state.get("last_refill", "unknown")
        print(f"✗ No charges remaining for '{anchor_name}'.")
        print(f"  Next calling card arrives on the new moon. (last refill: {last})")
        return

    now     = datetime.now()
    expires = now + timedelta(minutes=WINDOW_MINUTES)

    if dry_run:
        print(f"[dry-run] Would activate pocket anchor for '{anchor_name}'")
        print(f"  Window: {now.strftime('%H:%M')} → {expires.strftime('%H:%M')} ({WINDOW_MINUTES} min)")
        print(f"  Charges after: {anchor_state['charges'] - 1}")
        return

    anchor_state["charges"] -= 1
    anchor_state["active_session"] = {
        "activated_at": now.isoformat(),
        "expires_at":   expires.isoformat(),
    }
    save_state(state)

    print(f"✓ Pocket anchor opened: {anchor_name}")
    print(f"  The calling card dissolves. The door is open for {WINDOW_MINUTES} minutes.")
    print(f"  Window: {now.strftime('%H:%M')} → {expires.strftime('%H:%M')}")
    print(f"  Charges remaining: {anchor_state['charges']}")
    print()
    print(f"POCKET_ANCHOR_ACTIVE: {anchor_name}")
    print(f"POCKET_ANCHOR_EXPIRES: {expires.isoformat()}")


def cmd_status(player: str):
    state = load_state()
    ps    = get_player_state(state, player)
    visited = visited_anchors(player)

    if not visited:
        print(f"No physically-visited anchors for {player}.")
        return

    print(f"Pocket Anchors — {player}")
    print()
    for name in visited:
        anchor_state = ps.get(name, {"charges": 0, "last_refill": None})
        charges = anchor_state.get("charges", 0)
        sess    = active_session(anchor_state)

        status = ""
        if sess:
            expires   = datetime.fromisoformat(sess["expires_at"])
            remaining = int((expires - datetime.now()).total_seconds() / 60)
            status    = f"  ← SESSION ACTIVE ({remaining} min remaining)"
        elif charges == 0:
            status = "  ← no charges (next: new moon)"

        charge_str = "●" * charges + "○" * max(0, 1 - charges)
        print(f"  {charge_str}  {name}{status}")


def cmd_refill(player: str, dry_run: bool = False):
    """
    Issue one charge per physically-visited anchor that has 0 charges.
    Intended to run on the new moon (day 1 of each month via tick.py).
    """
    state   = load_state()
    ps      = get_player_state(state, player)
    visited = visited_anchors(player)
    today   = date.today().isoformat()

    if not visited:
        print(f"  No visited anchors for {player} — nothing to refill.")
        return

    refilled = []
    for name in visited:
        anchor_state = ps.setdefault(name, {"charges": 0, "last_refill": None})
        last = anchor_state.get("last_refill")

        # Only refill if this month hasn't been issued yet
        this_month = date.today().strftime("%Y-%m")
        if last and last.startswith(this_month):
            continue  # Already refilled this month

        if anchor_state.get("charges", 0) >= 1:
            continue  # Already has a charge, don't stack

        if not dry_run:
            anchor_state["charges"]     = 1
            anchor_state["last_refill"] = today
        refilled.append(name)

    if not dry_run:
        save_state(state)

    if refilled:
        prefix = "[dry-run] " if dry_run else ""
        print(f"  {prefix}Pocket anchor calling cards delivered to {player}:")
        for name in refilled:
            print(f"    ✉  {name}")
    else:
        print(f"  No new calling cards for {player} this month.")


def cmd_expire(player: str):
    """Clear expired sessions. Silent — called automatically."""
    state = load_state()
    ps    = get_player_state(state, player)
    now   = datetime.now()
    changed = False

    for anchor_state in ps.values():
        if not isinstance(anchor_state, dict):
            continue
        sess = anchor_state.get("active_session")
        if sess:
            expires = datetime.fromisoformat(sess["expires_at"])
            if now >= expires:
                anchor_state["active_session"] = None
                changed = True

    if changed:
        save_state(state)


def check_active(player: str, anchor_name: str):
    """
    Return active session dict if player has an open pocket window for anchor_name.
    Used by anchor-check.py. Returns None if no active session.
    """
    cmd_expire(player)
    state = load_state()
    ps    = get_player_state(state, player)

    for name, anchor_state in ps.items():
        if anchor_name.lower() in name.lower() or name.lower() in anchor_name.lower():
            sess = active_session(anchor_state)
            if sess:
                return {"anchor_name": name, **sess}
    return None


def main():
    parser = argparse.ArgumentParser(description="Pocket anchor — remote Outer Stacks access")
    sub    = parser.add_subparsers(dest="cmd")

    p_activate = sub.add_parser("activate", help="Spend a charge, open a 30-min session")
    p_activate.add_argument("player")
    p_activate.add_argument("anchor_name")
    p_activate.add_argument("--dry-run", action="store_true")

    p_status = sub.add_parser("status", help="Show charges and active sessions")
    p_status.add_argument("player")

    p_refill = sub.add_parser("refill", help="Issue monthly charges (called by tick.py on new moon)")
    p_refill.add_argument("player")
    p_refill.add_argument("--dry-run", action="store_true")

    p_expire = sub.add_parser("expire", help="Clear expired sessions")
    p_expire.add_argument("player")

    args = parser.parse_args()

    if args.cmd == "activate":
        cmd_activate(args.player, args.anchor_name, dry_run=args.dry_run)
    elif args.cmd == "status":
        cmd_status(args.player)
    elif args.cmd == "refill":
        cmd_refill(args.player, dry_run=args.dry_run)
    elif args.cmd == "expire":
        cmd_expire(args.player)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
