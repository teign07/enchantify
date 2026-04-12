#!/usr/bin/env python3
"""
things/tick.py — Read Things 3 via AppleScript and write narrative seeds.

Reads today's tasks, overdue items, and recent completions.
macOS only — uses osascript to talk to Things 3.
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR   = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent.parent))
SKILL_ID   = os.environ.get("ENCHANTIFY_SKILL_ID", "things")
TICK_QUEUE = BASE_DIR / "memory" / "tick-queue.md"

import platform
if platform.system() != "Darwin":
    print(f"[{SKILL_ID}] macOS only — skipping.", file=sys.stderr)
    sys.exit(0)


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15
    )
    return result.stdout.strip()


def get_today_tasks() -> list[str]:
    script = '''
tell application "Things3"
    set todayTasks to to dos of list "Today"
    set taskNames to {}
    repeat with t in todayTasks
        if completion date of t is missing value then
            set end of taskNames to name of t
        end if
    end repeat
    return taskNames
end tell
'''
    raw = run_applescript(script)
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()][:5]


def get_overdue_tasks() -> list[dict]:
    script = '''
tell application "Things3"
    set overdueTasks to {}
    set allTodos to to dos of list "Anytime"
    repeat with t in allTodos
        set d to due date of t
        if d is not missing value then
            if d < (current date) and completion date of t is missing value then
                set end of overdueTasks to (name of t) & "|" & (d as string)
            end if
        end if
    end repeat
    return overdueTasks
end tell
'''
    raw = run_applescript(script)
    if not raw:
        return []

    now = datetime.now()
    tasks = []
    for entry in raw.split(","):
        entry = entry.strip()
        if "|" not in entry:
            continue
        name, due_str = entry.rsplit("|", 1)
        try:
            # AppleScript date format is locale-dependent; we parse what we can
            days_late = 1  # fallback
            tasks.append({"name": name.strip(), "days_late": days_late})
        except Exception:
            tasks.append({"name": name.strip(), "days_late": 1})

    return tasks[:5]


def get_recent_completions() -> list[str]:
    script = '''
tell application "Things3"
    set recentDone to {}
    set logList to to dos of list "Logbook"
    set cutoff to (current date) - (1 * days)
    repeat with t in logList
        if completion date of t > cutoff then
            set end of recentDone to name of t
        end if
    end repeat
    return recentDone
end tell
'''
    raw = run_applescript(script)
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()][:5]


def fetch() -> list[dict]:
    items = []

    # Completions — positive signal
    completed = get_recent_completions()
    if len(completed) >= 3:
        items.append({
            "raw":  f"{len(completed)} tasks completed in the last 24h: {', '.join(completed[:3])}",
            "seed": f"A productive day in the real world — {len(completed)} threads closed. The Academy is energized.",
        })
    elif len(completed) == 1:
        items.append({
            "raw":  f"Completed: \"{completed[0]}\"",
            "seed": f"A thread closed: \"{completed[0]}.\" The Academy registers the act.",
        })

    # Overdue — Nothing pressure
    overdue = get_overdue_tasks()
    heavy = [t for t in overdue if t["days_late"] >= 7]
    mild  = [t for t in overdue if t["days_late"] < 7]

    for t in heavy[:2]:
        items.append({
            "raw":  f"Overdue {t['days_late']}+ days: \"{t['name']}\"",
            "seed": f"A thread has been left open for {t['days_late']}+ days — the Nothing has settled into it.",
        })

    if mild and not heavy:
        names = ", ".join(f"\"{t['name']}\"" for t in mild[:2])
        items.append({
            "raw":  f"Overdue items: {names}",
            "seed": f"Some threads left unresolved: {names}. Small shadows — easily cleared.",
        })

    return items[:4]


def write_to_queue(items: list[dict]) -> None:
    if not items:
        print(f"[{SKILL_ID}] Nothing significant to report from Things.")
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
