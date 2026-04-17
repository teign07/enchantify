"""
npc_log.py — NPC action memory.

Append when an NPC acts. Read by scene-director.py CAST layer to flag NPCs
with recent actions so the Labyrinth can let them bring it up in-game.

Action types:
  research       — NPC delivered a research note (npc-research.py)
  elective       — NPC assigned a quest to the player (update-player.py)
  belief_invest  — NPC invested Belief into a chapter talisman (tick.py)
  belief_fell    — NPC or entity Belief dropped significantly (world-pulse.py)

Pruned by labyrinth-intelligence.py after 7 days.
"""
import os
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent))
NPC_LOG  = BASE_DIR / "memory" / "npc-log.md"

_HEADER = (
    "# NPC Action Log\n"
    "*Actions NPCs have taken since their last appearance in play.*\n"
    "*Written by scripts. Read by Director's Slate CAST layer. Pruned nightly (7 days).*\n\n"
    "| Date | NPC | Type | Detail |\n"
    "|------|-----|------|--------|\n"
)


def append(npc_name: str, action_type: str, detail: str) -> None:
    """Append one NPC action to the log."""
    today  = date.today().isoformat()
    detail = detail.replace("|", "/").replace("\n", " ").strip()
    row    = f"| {today} | {npc_name} | {action_type} | {detail} |\n"
    NPC_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not NPC_LOG.exists():
        NPC_LOG.write_text(_HEADER)
    with NPC_LOG.open("a") as f:
        f.write(row)


def read_recent(days: int = 7) -> list[dict]:
    """Return recent entries as list of dicts, newest first."""
    if not NPC_LOG.exists():
        return []
    cutoff  = (date.today() - timedelta(days=days)).isoformat()
    entries = []
    for line in NPC_LOG.read_text().splitlines():
        if not line.startswith("|") or "---|" in line or "Date |" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4 or parts[0] < cutoff:
            continue
        entries.append({
            "date":   parts[0],
            "npc":    parts[1],
            "type":   parts[2],
            "detail": parts[3],
        })
    return list(reversed(entries))


def prune(days: int = 7) -> int:
    """Remove entries older than `days` days. Returns count removed."""
    if not NPC_LOG.exists():
        return 0
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    lines  = NPC_LOG.read_text().splitlines(keepends=True)
    kept, removed = [], 0
    for line in lines:
        if line.startswith("|") and "---|" not in line and "Date |" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 1 and parts[0] < cutoff:
                removed += 1
                continue
        kept.append(line)
    if removed:
        NPC_LOG.write_text("".join(kept))
    return removed
