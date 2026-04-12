#!/usr/bin/env python3
"""
obsidian/tick.py — Scan the Obsidian vault for new/modified notes.

Looks for notes created or modified in the last N days. Identifies orphans
(no outgoing links) and hubs (many links). Writes narrative seeds to
tick-queue.md for the Labyrinth to pick up.
"""
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR   = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent.parent))
SKILL_ID   = os.environ.get("ENCHANTIFY_SKILL_ID", "obsidian")
TICK_QUEUE = BASE_DIR / "memory" / "tick-queue.md"

VAULT_PATH = os.environ.get("ENCHANTIFY_OBSIDIAN_VAULT", "")
DAYS_BACK  = int(os.environ.get("ENCHANTIFY_OBSIDIAN_DAYS", "1"))

if not VAULT_PATH:
    print(f"[{SKILL_ID}] Missing config: ENCHANTIFY_OBSIDIAN_VAULT", file=sys.stderr)
    sys.exit(0)

VAULT = Path(VAULT_PATH).expanduser()
if not VAULT.exists():
    print(f"[{SKILL_ID}] Vault not found: {VAULT}", file=sys.stderr)
    sys.exit(0)

LINK_RE  = re.compile(r"\[\[([^\]|#]+)")
CUTOFF   = datetime.now() - timedelta(days=DAYS_BACK)


def get_all_notes() -> list[Path]:
    return [p for p in VAULT.rglob("*.md")
            if not any(part.startswith(".") for part in p.parts)]


def count_outgoing_links(path: Path) -> int:
    try:
        return len(LINK_RE.findall(path.read_text(errors="ignore")))
    except Exception:
        return 0


def count_incoming_links(path: Path, all_notes: list[Path]) -> int:
    stem = path.stem.lower()
    count = 0
    for note in all_notes:
        if note == path:
            continue
        try:
            links = [l.lower() for l in LINK_RE.findall(note.read_text(errors="ignore"))]
            if stem in links:
                count += 1
        except Exception:
            pass
    return count


def classify(path: Path, outgoing: int, incoming: int, is_new: bool, is_modified: bool) -> tuple[str, str]:
    """Return (raw description, narrative seed)."""
    age = "new" if is_new else "modified"
    size = path.stat().st_size
    word_est = size // 5  # rough estimate

    if incoming > 5:
        raw  = f"Hub note: '{path.stem}' ({incoming} citations, {word_est} words)"
        seed = f"A text in the Reading Room that everything else seems to reference — '{path.stem}' — has been updated."
    elif outgoing == 0 and incoming == 0:
        raw  = f"Orphan note: '{path.stem}' ({word_est} words, no links)"
        seed = f"An uncited manuscript sits alone in the Reading Room: '{path.stem}.' The Library has not filed it."
    elif is_new:
        raw  = f"New note: '{path.stem}' ({word_est} words, created recently)"
        seed = f"A fresh manuscript arrived in the Reading Room — '{path.stem}' — ink still settling."
    else:
        raw  = f"Revised note: '{path.stem}' ({word_est} words, modified recently)"
        seed = f"The player has been returning to '{path.stem}.' The margins are filling with second thoughts."

    return raw, seed


def fetch() -> list[dict]:
    all_notes = get_all_notes()
    items = []
    seen = set()

    for path in all_notes:
        try:
            stat = path.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)
            ctime = datetime.fromtimestamp(stat.st_ctime)

            is_new      = ctime > CUTOFF
            is_modified = mtime > CUTOFF and not is_new

            if not (is_new or is_modified):
                continue
            if path.stem in seen:
                continue
            seen.add(path.stem)

            outgoing = count_outgoing_links(path)
            incoming = count_incoming_links(path, all_notes)
            raw, seed = classify(path, outgoing, incoming, is_new, is_modified)
            items.append({"raw": raw, "seed": seed})

        except Exception:
            continue

    # Cap at 3 items per tick — don't flood the queue
    return items[:3]


def write_to_queue(items: list[dict]) -> None:
    if not items:
        print(f"[{SKILL_ID}] Nothing new in vault (last {DAYS_BACK}d).")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)

    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text(
            "# Tick Queue\n\n"
            "*Populated by skill-lore and tick.py. Read at session open.*\n\n---\n"
        )

    with TICK_QUEUE.open("a") as f:
        for item in items:
            f.write(
                f"\n## [{SKILL_ID}] {timestamp}\n"
                f"*Raw: {item['raw']}*\n"
                f"Narrative seed: {item['seed']}\n"
            )

    print(f"[{SKILL_ID}] Wrote {len(items)} seed(s) to tick queue.")


if __name__ == "__main__":
    try:
        write_to_queue(fetch())
    except Exception as e:
        print(f"[{SKILL_ID}] Error: {e}", file=sys.stderr)
        sys.exit(0)
