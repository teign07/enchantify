#!/usr/bin/env python3
"""
update-player.py — Reliable numeric state updates for player files.
Handles Belief, Tutorial Progress, NPC relationship scores, and quest tracking.
The Labyrinth calls this instead of editing numeric fields itself.

Usage:
  python3 scripts/update-player.py [player] belief [+N | -N | set N]
  python3 scripts/update-player.py [player] tutorial [T1-T14 | complete]
  python3 scripts/update-player.py [player] relationship "[NPC Name]" [+N | -N | set N] ["optional note"]
  python3 scripts/update-player.py [player] quest add "[description]" "[NPC Name]" [belief_reward] [rel_reward]
  python3 scripts/update-player.py [player] quest drop "[description]"
  python3 scripts/update-player.py [player] quest list

Examples:
  python3 scripts/update-player.py bj belief +9
  python3 scripts/update-player.py bj belief -2
  python3 scripts/update-player.py bj tutorial T9
  python3 scripts/update-player.py bj relationship "Zara Finch" +15 "helped find a lost book"
  python3 scripts/update-player.py bj quest add "Find what the harbour smells like at dawn" "Zara Finch" 3 25
  python3 scripts/update-player.py bj quest drop "Find what the harbour smells like at dawn"
  python3 scripts/update-player.py bj quest list
"""
import sys
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

PLAYERS_DIR = "players"
BELIEF_MIN = 0
BELIEF_MAX = 100

sys.path.insert(0, str(Path(__file__).parent))
try:
    import npc_log as _npc_log
    _HAS_NPC_LOG = True
except ImportError:
    _HAS_NPC_LOG = False


def load_player(name: str) -> tuple[str, str]:
    path = os.path.join(PLAYERS_DIR, f"{name}.md")
    if not os.path.exists(path):
        print(f"❌ Player file not found: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        return path, f.read()


def save_player(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)


def parse_delta(arg: str) -> tuple[str, int]:
    """Parse '+5', '-3', 'set 45' into (mode, value)."""
    arg = arg.strip()
    if arg.startswith("+"):
        return "delta", int(arg[1:])
    elif arg.startswith("-"):
        return "delta", -int(arg[1:])
    elif arg.lower().startswith("set"):
        parts = arg.split()
        return "set", int(parts[1]) if len(parts) > 1 else 0
    else:
        try:
            return "set", int(arg)
        except ValueError:
            print(f"❌ Cannot parse value: '{arg}'. Use +N, -N, or 'set N'.")
            sys.exit(1)


# ─── Belief ──────────────────────────────────────────────────────────────────

def update_belief(name: str, delta_arg: str):
    path, content = load_player(name)

    match = re.search(r'^- \*\*Belief:\*\* (\d+)', content, re.MULTILINE)
    if not match:
        print("❌ Could not find '- **Belief:** N' in player file.")
        sys.exit(1)

    current = int(match.group(1))
    mode, value = parse_delta(delta_arg)

    if mode == "delta":
        new_belief = current + value
    else:
        new_belief = value

    new_belief = max(BELIEF_MIN, min(BELIEF_MAX, new_belief))
    change = new_belief - current

    new_content = content[:match.start()] + f"- **Belief:** {new_belief}" + content[match.end():]
    save_player(path, new_content)

    arrow = "→" if change == 0 else ("↑" if change > 0 else "↓")
    print(f"✓ Belief updated: {current} {arrow} {new_belief}  (change: {change:+d})")

    # Narrative cue
    if new_belief == 0:
        print("  ⚠️  Belief at 0 — the world looks grayer. Offer a gentle path back.")
    elif new_belief == 100:
        print("  ✨ Belief at 100 — everything shimmers. Don't let them hoard it.")
    elif new_belief <= 25:
        print("  📎 Belief ≤ 25 — offer a Compass Run. Early warning threshold.")
    elif new_belief < 40:
        print("  📎 Belief below 40 — offer an Enchantment opportunity.")


# ─── Tutorial Progress ───────────────────────────────────────────────────────

def update_tutorial(name: str, step: str):
    path, content = load_player(name)

    step = step.strip().upper()
    # Normalize "complete" or "T14" both to "T14"
    if step.lower() in ("complete", "t14"):
        step = "T14"
    elif not re.match(r'^T\d+$', step):
        print(f"❌ Invalid tutorial step: '{step}'. Use T1–T14 or 'complete'.")
        sys.exit(1)

    match = re.search(r'^- \*\*Tutorial Progress:\*\* .+', content, re.MULTILINE)
    if not match:
        print("❌ Could not find '- **Tutorial Progress:**' in player file.")
        sys.exit(1)

    old_line = match.group(0)
    new_line = f"- **Tutorial Progress:** {step}"
    new_content = content[:match.start()] + new_line + content[match.end():]
    save_player(path, new_content)

    old_val = old_line.split('**')[-1].strip()
    print(f"✓ Tutorial Progress: {old_val} → {step}")
    if step == "T14":
        print("  🎓 Tutorial complete. The rails are gone. Transition to open world.")


# ─── NPC Relationships ───────────────────────────────────────────────────────

def update_relationship(name: str, npc_name: str, delta_arg: str, note: str = ""):
    path, content = load_player(name)

    mode, value = parse_delta(delta_arg)

    # Find an existing row for this NPC in any relationship table
    # Matches: | NPC Name | Chapter | Score | Notes |
    row_pattern = re.compile(
        r'(\| ' + re.escape(npc_name) + r' \| [^|]+ \| )([+-]?\d+)( \| [^|]* \|)',
        re.MULTILINE
    )
    match = row_pattern.search(content)

    if match:
        current_score = int(match.group(2))
        if mode == "delta":
            new_score = current_score + value
        else:
            new_score = value

        new_score = max(-100, min(100, new_score))
        score_str = f"{new_score:+d}" if new_score != 0 else "0"

        # Build updated row, appending note if provided
        old_notes_col = match.group(3)  # " | existing notes |"
        if note:
            existing_notes = old_notes_col.strip(" |").strip()
            new_notes = f"{existing_notes} {note}".strip() if existing_notes else note
            new_notes_col = f" | {new_notes} |"
        else:
            new_notes_col = old_notes_col

        replacement = match.group(1) + score_str + new_notes_col
        new_content = content[:match.start()] + replacement + content[match.end():]
        save_player(path, new_content)

        change = new_score - current_score
        print(f"✓ Relationship updated: {npc_name}  {current_score:+d} → {new_score:+d}  (change: {change:+d})")

    else:
        # NPC not in table yet — create or append to Relationships section
        new_score = value if mode == "set" else value  # delta from 0 if new
        new_score = max(-100, min(100, new_score))
        score_str = f"{new_score:+d}" if new_score != 0 else "0"
        note_text = note if note else "First interaction."

        new_row = f"| {npc_name} | — | {score_str} | {note_text} |"

        # Find the Relationships table header
        table_header = re.search(
            r'(\| NPC \| Chapter \| Score \| Notes \|\n\|[-| ]+\|\n)',
            content, re.MULTILINE
        )
        if table_header:
            insert_at = table_header.end()
            new_content = content[:insert_at] + new_row + "\n" + content[insert_at:]
        else:
            # No table yet — append a Relationships section
            relationships_section = (
                "\n## Relationships\n\n"
                "| NPC | Chapter | Score | Notes |\n"
                "|---|---|---|---|\n"
                f"{new_row}\n"
            )
            new_content = content.rstrip() + "\n" + relationships_section

        save_player(path, new_content)
        print(f"✓ New relationship added: {npc_name}  {new_score:+d}")

    # Narrative cue for extreme scores
    if abs(new_score) >= 75:
        level = "Close Friend / Devoted" if new_score > 0 else "Enemy / Mortal Enemy"
        print(f"  ⚡ Score {new_score:+d} — relationship level: {level}")


# ─── Quest / Inside Cover ────────────────────────────────────────────────────

QUEST_CAPACITY = 5
COVER_PLACEHOLDER = "*(empty — the cover is clean)*"


def _get_cover_section(content: str):
    """Return (table_header_match, body_start, body_end) for The Inside Cover table."""
    header = re.search(
        r'\| Quest \| NPC \| Belief \| Relationship \|\n\|[-| ]+\|\n',
        content, re.MULTILINE
    )
    return header


def _parse_quests(content: str) -> list[dict]:
    """Return list of active quests from The Inside Cover table."""
    header = _get_cover_section(content)
    if not header:
        return []

    body_start = header.end()
    # Read until next ## section or end of file
    next_section = re.search(r'\n## ', content[body_start:])
    body_end = body_start + next_section.start() if next_section else len(content)
    table_body = content[body_start:body_end]

    quests = []
    for line in table_body.splitlines():
        if not line.startswith('|') or COVER_PLACEHOLDER in line:
            continue
        parts = [p.strip() for p in line.split('|')[1:-1]]
        if not parts or not parts[0]:
            continue
        # Standard format: | description | NPC | belief_reward | rel_reward |
        if len(parts) >= 4:
            try:
                quests.append({
                    'description': parts[0],
                    'npc': parts[1],
                    'belief': int(parts[2].strip('+')),
                    'relationship': int(parts[3].strip('+')),
                })
                continue
            except (ValueError, IndexError):
                pass
        # Legacy / manually-written format: | NPC | description | **ACTIVE** |
        # Count it as an active quest even without numeric rewards
        non_empty = [p for p in parts if p and '---|' not in p and p != '---']
        if len(non_empty) >= 2:
            quests.append({
                'description': non_empty[1] if len(non_empty) > 1 else non_empty[0],
                'npc': non_empty[0],
                'belief': 0,
                'relationship': 0,
            })
    return quests


def quest_add(name: str, description: str, npc: str, belief_reward: int, rel_reward: int):
    path, content = load_player(name)

    quests = _parse_quests(content)
    if len(quests) >= QUEST_CAPACITY:
        print(f"❌ The Inside Cover is full ({QUEST_CAPACITY} active quests). Drop one first.")
        sys.exit(1)

    for q in quests:
        if q['description'].lower() == description.lower():
            print(f"❌ Quest already on the cover: '{description}'")
            sys.exit(1)

    new_row = f"| {description} | {npc} | +{belief_reward} | +{rel_reward} |"

    header = _get_cover_section(content)
    if header:
        insert_at = header.end()
        # Remove placeholder row if present
        placeholder_re = re.compile(
            r'\| \*\(empty[^|]*\)\* \| \| \| \|\n', re.MULTILINE
        )
        placeholder = placeholder_re.search(content, insert_at)
        if placeholder and placeholder.start() == insert_at:
            content = content[:placeholder.start()] + new_row + "\n" + content[placeholder.end():]
        else:
            content = content[:insert_at] + new_row + "\n" + content[insert_at:]
    else:
        # No section yet — append it
        cover_section = (
            "\n## The Inside Cover\n\n"
            "| Quest | NPC | Belief | Relationship |\n"
            "|---|---|---|---|\n"
            f"{new_row}\n"
        )
        content = content.rstrip() + "\n" + cover_section

    save_player(path, content)
    if _HAS_NPC_LOG:
        _npc_log.append(npc, "elective", description[:100])
    total = len(quests) + 1
    print(f"✓ Quest tucked into The Inside Cover: '{description}'")
    print(f"  NPC: {npc} | Reward: +{belief_reward} Belief, +{rel_reward} rel  ({total}/{QUEST_CAPACITY} active)")

    # Notify player — they may not be watching the narration
    desc_safe = description.replace('"', '\\"')
    npc_safe = npc.replace('"', '\\"')
    notif = (
        f'display notification "{npc_safe} has written in your Inside Cover" '
        f'with title "New Quest" subtitle "{desc_safe}" sound name "default"'
    )
    subprocess.run(["osascript", "-e", notif], capture_output=True, timeout=5)

    # Sync to Apple Reminders
    reminder_title = f"{npc_safe}: {desc_safe}"
    try:
        subprocess.run(["remindctl", "add", "--title", reminder_title, "--list", "Academy"], capture_output=True, timeout=5)
        print(f"  ✓ Synced to Apple Reminders (Academy list)")
    except Exception as e:
        print(f"  [Warning] Could not sync to Apple Reminders: {e}")


def quest_drop(name: str, description: str) -> Optional[dict]:
    """Remove a quest row. Returns quest data if found, or None on failure.
    Pass silent=True to suppress output (used by complete-quest.py)."""
    path, content = load_player(name)
    quests = _parse_quests(content)

    target = next((q for q in quests if q['description'].lower() == description.lower()), None)
    if not target:
        print(f"❌ Quest not found: '{description}'")
        print("  Use 'quest list' to see active quests.")
        sys.exit(1)

    # Remove the row (match on actual description text)
    row_re = re.compile(
        r'\| ' + re.escape(target['description']) + r' \| [^|\n]* \| [^|\n]* \| [^|\n]* \|\n',
        re.MULTILINE
    )
    content = row_re.sub('', content, count=1)

    # If table is now empty, restore placeholder
    remaining = _parse_quests(content)
    if not remaining:
        header = _get_cover_section(content)
        if header:
            placeholder = f"| {COVER_PLACEHOLDER} | | | |\n"
            content = content[:header.end()] + placeholder + content[header.end():]

    save_player(path, content)
    return target


def quest_list(name: str):
    _, content = load_player(name)
    quests = _parse_quests(content)

    if not quests:
        print(f"📖 The Inside Cover is empty.")
        return

    print(f"📖 The Inside Cover ({len(quests)}/{QUEST_CAPACITY} active):")
    for i, q in enumerate(quests, 1):
        print(f"  {i}. \"{q['description']}\"")
        print(f"     NPC: {q['npc']} | Reward: +{q['belief']} Belief, +{q['relationship']} rel")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    player = sys.argv[1]
    field = sys.argv[2].lower()

    if field == "belief":
        if len(sys.argv) < 4:
            print("❌ Usage: update-player.py [player] belief [+N | -N | set N]")
            sys.exit(1)
        update_belief(player, sys.argv[3])

    elif field == "tutorial":
        if len(sys.argv) < 4:
            print("❌ Usage: update-player.py [player] tutorial [T1-T14 | complete]")
            sys.exit(1)
        update_tutorial(player, sys.argv[3])

    elif field == "relationship":
        if len(sys.argv) < 5:
            print('❌ Usage: update-player.py [player] relationship "[NPC Name]" [+N | -N | set N] ["optional note"]')
            sys.exit(1)
        npc_name = sys.argv[3]
        delta_arg = sys.argv[4]
        note = sys.argv[5] if len(sys.argv) > 5 else ""
        update_relationship(player, npc_name, delta_arg, note)

    elif field == "quest":
        subcommand = sys.argv[3].lower() if len(sys.argv) > 3 else ""
        if subcommand == "add":
            if len(sys.argv) < 8:
                print('❌ Usage: update-player.py [player] quest add "[description]" "[NPC]" [belief] [rel]')
                sys.exit(1)
            quest_add(player, sys.argv[4], sys.argv[5], int(sys.argv[6]), int(sys.argv[7]))
        elif subcommand == "drop":
            if len(sys.argv) < 5:
                print('❌ Usage: update-player.py [player] quest drop "[description]"')
                sys.exit(1)
            quest_drop(player, sys.argv[4])
            print(f"✓ Quest dropped. The note dissolves into harmless ink.")
        elif subcommand == "list":
            quest_list(player)
        else:
            print(f"❌ Unknown quest subcommand: '{subcommand}'. Use: add, drop, list.")
            sys.exit(1)

    else:
        print(f"❌ Unknown field: '{field}'. Use: belief, tutorial, relationship, quest.")
        sys.exit(1)


if __name__ == "__main__":
    main()
