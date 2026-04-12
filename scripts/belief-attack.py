#!/usr/bin/env python3
"""
belief-attack.py — Execute a Belief exchange between any two entities.

The attacker rolls dice (using their own Belief score) to determine the outcome.
The Labyrinth sets the difficulty; the dice set the deal amount.

DICE MODE (default):
  Provide --spend and --difficulty. The script rolls d100 using the attacker's
  Belief score and maps the result to a deal amount:

    CRITICAL SUCCESS  → spend × 1.5 (spend 5 → deal 7–8)
    SUCCESS           → spend × 1.0 (spend 5 → deal 5)
    NEAR MISS         → spend × 0.5, min 1 (partial — something landed)
    FAILURE           → 0 (attacker spent, nothing landed)
    CRITICAL FAILURE  → backfire — attacker takes spend as EXTRA damage too

EXPLICIT MODE (for passive/environmental attacks, no roll):
  Provide --deal N to skip the dice. Used for The Nothing's slow ambient drain,
  atmospheric decay, or other effects where no active roll makes sense.

Floors (enforced automatically):
  player, nothing  → min 0
  entity, npc, talisman, location, object  → min 5

Usage:
  # Dice mode — most combat, debates, arguments
  python3 scripts/belief-attack.py \\
    --from "bj" --from-type player \\
    --to "Wicker Eddies" --to-type entity \\
    --spend 5 --difficulty standard \\
    --note "Sharp argument in the Great Hall"

  # Explicit mode — environmental / passive effects
  python3 scripts/belief-attack.py \\
    --from "The Nothing" --from-type nothing \\
    --to "Wind Cipher" --to-type talisman \\
    --spend 0 --deal 3 \\
    --note "Three flat sessions — the Cipher dims"

Options:
  --no-floor    Override minimum Belief floors (story-critical moments only)
  --dry-run     Show what would happen without writing anything
"""
import re
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Allow importing dice.py from the same directory
import sys
sys.path.insert(0, str(Path(__file__).parent))
from dice import roll_d100, combat_deal, DIFFICULTY_MODIFIERS

BASE_DIR   = Path(__file__).parent.parent
REGISTER   = BASE_DIR / "lore" / "world-register.md"
COMBAT_LOG = BASE_DIR / "logs" / "belief-combat.md"

FLOORS = {
    "player":   0,
    "nothing":  0,
    "entity":   5,
    "npc":      5,
    "talisman": 5,
    "location": 5,
    "object":   5,
}

OUTCOME_LABELS = {
    "CRITICAL_SUCCESS": "✨ CRITICAL SUCCESS",
    "SUCCESS":          "✅ SUCCESS",
    "NEAR_MISS":        "⚡ NEAR MISS",
    "FAILURE":          "❌ FAILURE",
    "CRITICAL_FAILURE": "💀 CRITICAL FAILURE — BACKFIRE",
}


def get_floor(entity_type, no_floor=False):
    if no_floor:
        return 0
    return FLOORS.get(entity_type.lower(), 5)


# ── World-register helpers ────────────────────────────────────────────────────

def get_entity_belief(register_text, name):
    m = re.search(
        r"^\|\s*" + re.escape(name) + r"\s*\|\s*[\w][\w\s]*\s*\|\s*(\d+)\s*\|",
        register_text, re.MULTILINE
    )
    if m:
        return int(m.group(1))
    m = re.search(
        r"^-\s*" + re.escape(name) + r"\s*\([\w][\w\s]*,\s*Belief\s*(\d+)\)",
        register_text, re.MULTILINE
    )
    return int(m.group(1)) if m else None


def set_entity_belief(register_text, name, new_value):
    new_text = re.sub(
        r"(\|\s*" + re.escape(name) + r"\s*\|\s*[\w][\w\s]*\s*\|\s*)\d+(\s*\|)",
        rf"\g<1>{new_value}\g<2>",
        register_text, flags=re.MULTILINE
    )
    new_text = re.sub(
        r"(-\s*" + re.escape(name) + r"\s*\([\w][\w\s]*,\s*Belief\s*)\d+(\))",
        rf"\g<1>{new_value}\g<2>",
        new_text, flags=re.MULTILINE
    )
    return new_text


def write_register(new_text):
    backup = REGISTER.with_suffix(".md.bak")
    shutil.copy2(REGISTER, backup)
    tmp = REGISTER.with_suffix(".md.tmp")
    tmp.write_text(new_text if new_text.endswith("\n") else new_text + "\n")
    tmp.rename(REGISTER)


# ── Player helpers ─────────────────────────────────────────────────────────────

def get_player_belief(player_name):
    player_file = BASE_DIR / "players" / f"{player_name}.md"
    if not player_file.exists():
        return None
    text = player_file.read_text()
    m = re.search(r"\*\*Belief:\*\*\s*(\d+)", text)
    return int(m.group(1)) if m else None


def update_player_belief(player_name, delta):
    sign = "+" if delta >= 0 else ""
    result = subprocess.run(
        ["python3", str(BASE_DIR / "scripts" / "update-player.py"),
         player_name, "belief", f"{sign}{delta}"],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout + result.stderr


# ── Combat log ─────────────────────────────────────────────────────────────────

def log_exchange(attacker, attacker_type, att_before, att_after,
                 target, target_type, tgt_before, tgt_after,
                 spent, dealt, note, roll_result, dry_run):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    roll_line = ""
    if roll_result:
        label = OUTCOME_LABELS.get(roll_result["outcome"], roll_result["outcome"])
        roll_line = (
            f"Roll: {roll_result['roll']} vs threshold {roll_result['threshold']} "
            f"(Belief {roll_result['belief']}, {roll_result['difficulty']}) → {label}\n"
        )

    entry = (
        f"\n## {timestamp}\n"
        f"{roll_line}"
        f"**{attacker}** ({attacker_type}) spent {spent} → Belief {att_before} → {att_after}\n"
        f"**{target}** ({target_type}) took {dealt} → Belief {tgt_before} → {tgt_after}\n"
    )
    if note:
        entry += f"*{note}*\n"

    if dry_run:
        print(f"\n[dry-run] Would log:\n{entry}")
        return

    COMBAT_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not COMBAT_LOG.exists():
        COMBAT_LOG.write_text(
            "# Belief Combat Log\n\n"
            "*All Belief exchanges. Written by belief-attack.py.*\n"
        )
    with COMBAT_LOG.open("a") as f:
        f.write(entry)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Execute a Belief attack between two entities")
    parser.add_argument("--from",       dest="attacker",      required=True)
    parser.add_argument("--from-type",  dest="attacker_type", required=True,
                        help="player | entity | npc | talisman | nothing | location | object")
    parser.add_argument("--to",         dest="target",        required=True)
    parser.add_argument("--to-type",    dest="target_type",   required=True)
    parser.add_argument("--spend",      type=int,             required=True,
                        help="Belief committed by attacker (can be 0 for passive attacks)")
    parser.add_argument("--difficulty", default=None,
                        choices=list(DIFFICULTY_MODIFIERS.keys()),
                        help="Dice difficulty — omit only when using explicit --deal")
    parser.add_argument("--deal",       type=int,             default=None,
                        help="Explicit damage (skips dice roll — for environmental/passive effects)")
    parser.add_argument("--note",       default="",           help="Narrative context (logged)")
    parser.add_argument("--no-floor",   action="store_true",  help="Override minimum Belief floors")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()

    # Validate: need either --difficulty (dice) or --deal (explicit)
    if args.deal is None and args.difficulty is None:
        parser.error("Provide --difficulty [routine|standard|dramatic|desperate] for dice mode, "
                     "or --deal N for explicit mode.")

    attacker_floor = get_floor(args.attacker_type, args.no_floor)
    target_floor   = get_floor(args.target_type,   args.no_floor)

    # ── Read current Belief values ─────────────────────────────────────────────
    register_text = REGISTER.read_text() if REGISTER.exists() else ""

    if args.attacker_type.lower() == "player":
        attacker_belief = get_player_belief(args.attacker)
        if attacker_belief is None:
            print(f"❌ Player '{args.attacker}' not found.")
            return
    else:
        attacker_belief = get_entity_belief(register_text, args.attacker)
        if attacker_belief is None:
            print(f"❌ Entity '{args.attacker}' not found in world-register.md.")
            return

    if args.target_type.lower() == "player":
        target_belief = get_player_belief(args.target)
        if target_belief is None:
            print(f"❌ Player '{args.target}' not found.")
            return
    else:
        target_belief = get_entity_belief(register_text, args.target)
        if target_belief is None:
            print(f"❌ Entity '{args.target}' not found in world-register.md.")
            return

    # ── Roll or use explicit deal ──────────────────────────────────────────────
    roll_result  = None
    backfire     = False
    raw_deal     = args.deal  # explicit mode

    if args.deal is None:
        # Dice mode — roll using attacker's Belief
        roll_result = roll_d100(attacker_belief, args.difficulty)
        raw_deal    = combat_deal(args.spend, roll_result)
        label       = OUTCOME_LABELS.get(roll_result["outcome"], roll_result["outcome"])

        print(f"\n--- BELIEF COMBAT ROLL ---")
        print(f"{args.attacker} ({args.attacker_type})  Belief {attacker_belief}  "
              f"| Difficulty: {args.difficulty}")
        print(f"Threshold: ≤ {roll_result['threshold']}  |  Rolled: {roll_result['roll']}")
        print(f"→ {label}")

        if raw_deal < 0:
            backfire = True
            print(f"💀 BACKFIRE — {args.attacker} takes {abs(raw_deal)} extra Belief damage")
        elif raw_deal == 0:
            print(f"Attack spent, nothing landed on {args.target}.")
        else:
            print(f"→ {args.attacker} deals {raw_deal} Belief damage to {args.target}")
        print(f"--- END ROLL ---\n")

    # ── Clamp spend to what attacker can afford above their floor ─────────────
    actual_spend = min(args.spend, max(0, attacker_belief - attacker_floor))

    # ── Handle backfire ────────────────────────────────────────────────────────
    if backfire:
        # Attacker takes spend-as-deal damage (on top of spend cost)
        backlash_damage = min(abs(raw_deal), max(0, attacker_belief - actual_spend - attacker_floor))
        actual_deal     = 0
        attacker_new    = attacker_belief - actual_spend - backlash_damage
        target_new      = target_belief   # target unaffected
    else:
        actual_deal  = min(raw_deal, max(0, target_belief - target_floor))
        attacker_new = attacker_belief - actual_spend
        target_new   = target_belief   - actual_deal

    # ── Print summary ──────────────────────────────────────────────────────────
    print(f"Exchange:")
    print(f"  {args.attacker} ({args.attacker_type}): {attacker_belief} → {attacker_new}  (spent {actual_spend})")
    if backfire:
        print(f"  {args.target} ({args.target_type}): {target_belief} → {target_new}  (unaffected)")
    else:
        print(f"  {args.target} ({args.target_type}): {target_belief} → {target_new}  (took {actual_deal})")
    if actual_spend != args.spend:
        print(f"  ⚠ Floor {attacker_floor} capped spend at {actual_spend} (requested {args.spend})")
    if not backfire and actual_deal != raw_deal and raw_deal > 0:
        print(f"  ⚠ Floor {target_floor} capped damage at {actual_deal} (raw {raw_deal})")
    if args.note:
        print(f"  Note: {args.note}")

    if args.dry_run:
        print("[dry-run] No files written.")
        return

    # ── Write changes ──────────────────────────────────────────────────────────
    register_modified = False

    # Attacker
    if args.attacker_type.lower() == "player":
        ok, msg = update_player_belief(args.attacker, -actual_spend)
        if not ok:
            print(f"❌ Failed to update player '{args.attacker}': {msg}")
            return
        if backfire and backlash_damage > 0:
            ok, msg = update_player_belief(args.attacker, -backlash_damage)
            if not ok:
                print(f"❌ Failed to apply backfire to '{args.attacker}': {msg}")
                return
    else:
        register_text   = set_entity_belief(register_text, args.attacker, attacker_new)
        register_modified = True

    # Target (only if not a backfire)
    if not backfire:
        if args.target_type.lower() == "player":
            ok, msg = update_player_belief(args.target, -actual_deal)
            if not ok:
                print(f"❌ Failed to update player '{args.target}': {msg}")
                return
        else:
            register_text   = set_entity_belief(register_text, args.target, target_new)
            register_modified = True

    if register_modified:
        write_register(register_text)

    log_exchange(
        args.attacker, args.attacker_type, attacker_belief, attacker_new,
        args.target, args.target_type, target_belief, target_new,
        actual_spend, actual_deal, args.note, roll_result, args.dry_run
    )

    print(f"✓ Exchange complete.")


if __name__ == "__main__":
    main()
