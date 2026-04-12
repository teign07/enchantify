#!/usr/bin/env python3
"""
complete-quest.py — Full quest completion flow for Enchantify.

When a player delivers a field report (text description or photo description),
this script handles everything: removes the quest from The Inside Cover,
applies Belief and relationship rewards, writes a field report file, and
appends to the Story Log.

The Labyrinth calls this after receiving and interpreting the player's report.

Usage:
  python3 scripts/complete-quest.py [player] "[quest description]" "[field report text]"

Options:
  --dry-run     Print what would happen without writing anything
  --fae         Fae bargain mode: skips Belief reward, marks report as fae bargain,
                leaves a lore fragment placeholder for the Labyrinth to fill in

Examples:
  python3 scripts/complete-quest.py bj "Find what the harbour smells like at dawn" "Salt and diesel. It smelled like beginnings."
  python3 scripts/complete-quest.py bj "Describe the old bookshop on 4th" "Felt like someone had pressed time between the pages." --dry-run
  python3 scripts/complete-quest.py bj "Find something with the color loud" "The fire hydrant on the corner. Red so red it was almost a sound." --fae
"""

import sys
import os
import re
import subprocess
import json
from datetime import date
from typing import Optional

PLAYERS_DIR = "players"
REPORTS_DIR = "memory/field-reports"
SCRIPTS_DIR = "scripts"


def load_player(name: str) -> tuple[str, str]:
    path = os.path.join(PLAYERS_DIR, f"{name}.md")
    if not os.path.exists(path):
        print(f"❌ Player file not found: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        return path, f.read()


def find_quest(content: str, description: str) -> Optional[dict]:
    """Parse The Inside Cover to find a quest matching the description."""
    header = re.search(
        r'\| Quest \| NPC \| Belief \| Relationship \|\n\|[-| ]+\|\n',
        content, re.MULTILINE
    )
    if not header:
        return None

    body_start = header.end()
    next_section = re.search(r'\n## ', content[body_start:])
    body_end = body_start + next_section.start() if next_section else len(content)
    table_body = content[body_start:body_end]

    desc_lower = description.lower()
    for line in table_body.splitlines():
        if not line.startswith('|') or '*(empty' in line:
            continue
        parts = [p.strip() for p in line.split('|')[1:-1]]
        if len(parts) < 4:
            continue
        if parts[0].lower() == desc_lower:
            try:
                return {
                    'description': parts[0],
                    'npc': parts[1],
                    'belief': int(parts[2].strip('+')),
                    'relationship': int(parts[3].strip('+')),
                }
            except (ValueError, IndexError):
                continue

    return None


def run_update_player(args: list[str], dry_run: bool = False) -> bool:
    cmd = ["python3", os.path.join(SCRIPTS_DIR, "update-player.py")] + args
    if dry_run:
        print(f"  [dry-run] Would run: {' '.join(cmd)}")
        return True
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    if result.returncode != 0:
        if result.stderr:
            print(f"  ❌ {result.stderr.strip()}")
        return False
    return True


def slugify(text: str) -> str:
    """Convert text to a kebab-slug for filenames."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:40]


def write_field_report(
    player: str,
    quest: dict,
    report_text: str,
    today: str,
    dry_run: bool = False,
    fae: bool = False,
):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    npc_slug = slugify(quest['npc'])
    prefix = "fae-" if fae else ""
    filename = f"{today}-{prefix}{npc_slug}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    # Handle existing file for same NPC same day — append a counter
    if os.path.exists(filepath):
        counter = 2
        while os.path.exists(filepath):
            filename = f"{today}-{prefix}{npc_slug}-{counter}.md"
            filepath = os.path.join(REPORTS_DIR, filename)
            counter += 1

    if fae:
        content = f"""# Fae Bargain: {quest['description']}

**Date:** {today}
**Player:** {player}
**Fae:** {quest['npc']}
**Reward:** +{quest['relationship']} relationship with {quest['npc']}

---

## Field Report

{report_text}

---

## Lore Fragment

*(The Labyrinth fills this in — something true about the Labyrinth not written anywhere else.)*

---

*This bargain was fulfilled. The {quest['npc']} accepted the report.*
*Incorporate the player's specific sensory details into future {quest['npc']} interactions.*
"""
    else:
        content = f"""# Field Report: {quest['description']}

**Date:** {today}
**Player:** {player}
**Requesting NPC:** {quest['npc']}
**Reward:** +{quest['belief']} Belief, +{quest['relationship']} relationship

---

## Report

{report_text}

---

*This report was delivered to {quest['npc']} and woven into Academy lore.*
*The Labyrinth should incorporate the player's specific details into future {quest['npc']} dialogue.*
"""

    if dry_run:
        print(f"  [dry-run] Would write field report to: {filepath}")
        return filepath

    with open(filepath, "w") as f:
        f.write(content)

    print(f"  ✓ Field report saved: {filepath}")
    return filepath


def append_story_log(path: str, content: str, quest: dict, today: str, dry_run: bool = False) -> str:
    log_entry = (
        f"- **{today}:** Completed field report for {quest['npc']}: "
        f"\"{quest['description']}\" "
        f"(+{quest['belief']} Belief, +{quest['relationship']} rel)"
    )

    # Find story log section and append
    log_match = re.search(r'(## 📜 Story Log\n)', content, re.MULTILINE)
    if log_match:
        insert_at = log_match.end()
        new_content = content[:insert_at] + log_entry + "\n" + content[insert_at:]
    else:
        new_content = content.rstrip() + f"\n\n## 📜 Story Log\n{log_entry}\n"

    if not dry_run:
        with open(path, "w") as f:
            f.write(new_content)
        print(f"  ✓ Story Log updated")

    return log_entry


def main():
    dry_run = "--dry-run" in sys.argv
    fae = "--fae" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--dry-run", "--fae")]

    if len(args) < 3:
        print(__doc__)
        sys.exit(1)

    player = args[0]
    description = args[1]
    report_text = args[2]
    today = date.today().isoformat()

    print(f"\n{'🌿' if fae else '📖'} {'Fae Bargain Fulfilled' if fae else 'Quest Completion'} — {player}")
    print(f"   Quest: \"{description}\"")
    if dry_run:
        print("   [DRY RUN — no changes will be written]\n")
    elif fae:
        print("   [FAE MODE — Belief skipped, lore fragment placeholder written]\n")
    else:
        print()

    # ── 1. Find the quest ────────────────────────────────────────────────────
    path, content = load_player(player)
    quest = find_quest(content, description)

    if not quest:
        print(f"❌ Quest not found on The Inside Cover: \"{description}\"")
        print(f"   Use: python3 scripts/update-player.py {player} quest list")
        sys.exit(1)

    print(f"  Found: \"{quest['description']}\"")
    print(f"  NPC: {quest['npc']}")
    print(f"  Rewards: +{quest['belief']} Belief, +{quest['relationship']} relationship\n")

    # ── 2. Remove quest from The Inside Cover ────────────────────────────────
    print("Step 1 — Remove from The Inside Cover:")
    success = run_update_player([player, "quest", "drop", quest['description']], dry_run)
    if not success and not dry_run:
        print("❌ Failed to remove quest. Aborting.")
        sys.exit(1)

    # Reload content after drop (file was modified)
    if not dry_run:
        _, content = load_player(player)
        
        # Sync to Apple Reminders (Mark Complete)
        try:
            result = subprocess.run(["remindctl", "list", "Academy", "--json"], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                reminders = json.loads(result.stdout)
                target_title = f"{quest['npc']}: {quest['description']}"
                for r in reminders:
                    if r.get('title') == target_title:
                        subprocess.run(["remindctl", "complete", str(r['id'])])
                        print("  ✓ Marked complete in Apple Reminders")
                        break
        except Exception as e:
            print(f"  [Warning] Could not sync completion to Apple Reminders: {e}")

    # ── 3. Apply Belief reward (skipped for fae bargains) ───────────────────
    print(f"\nStep 2 — Apply Belief reward (+{quest['belief']}):")
    if fae:
        print("  [fae bargain — Belief reward skipped]")
    else:
        run_update_player([player, "belief", f"+{quest['belief']}"], dry_run)

    # ── 4. Apply relationship boost ──────────────────────────────────────────
    print(f"\nStep 3 — Apply relationship boost to {quest['npc']} (+{quest['relationship']}):")
    note = f"delivered field report: {quest['description'][:50]}"
    run_update_player([player, "relationship", quest['npc'], f"+{quest['relationship']}", note], dry_run)

    # ── 5. Write field report file ───────────────────────────────────────────
    print(f"\nStep 4 — Write field report:")
    report_path = write_field_report(player, quest, report_text, today, dry_run, fae)

    # ── 6. Append to Story Log ───────────────────────────────────────────────
    print(f"\nStep 5 — Update Story Log:")
    if dry_run:
        print(f"  [dry-run] Would append log entry for {today}")
    else:
        append_story_log(path, content, quest, today)

    # ── 7. Narration summary ─────────────────────────────────────────────────
    if fae:
        print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌿 BARGAIN FULFILLED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bargain: "{quest['description']}"
Fae:     {quest['npc']}

Field report saved to: {report_path}

NARRATION NOTES FOR THE LABYRINTH:
- Narrate the {quest['npc']}'s response in character — their specific reaction to what was found.
- Then deliver the lore fragment: something true about the Labyrinth not written anywhere else.
  Write it into the field report file under ## Lore Fragment before the session closes.
- The player's specific sensory detail should surface again in future {quest['npc']} encounters.
- Relationship with {quest['npc']} is now warmer — let it show in how they approach next time.
- The bargain mark fades from the cover. The debt is paid.
""")
    else:
        print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ QUEST COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quest:  "{quest['description']}"
NPC:    {quest['npc']}

Field report saved to: {report_path}

NARRATION NOTES FOR THE LABYRINTH:
- Weave the player's specific sensory details into {quest['npc']}'s next scene.
- {quest['npc']} should reference what the player found — name it, incorporate it.
- The Souvenir Hall (if applicable) gains a new entry from the Unwritten Chapter.
- Relationship with {quest['npc']} is now significantly warmer — let it show naturally.
- The quest note physically dissolves from the cover in a curl of ink.
""")


if __name__ == "__main__":
    main()
