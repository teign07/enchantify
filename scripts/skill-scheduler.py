#!/usr/bin/env python3
"""
skill-scheduler.py — Discovers and runs skill-lore tick scripts.

Scans skill-lore/ for manifest.md files, finds those matching the requested
trigger type, sources enchantify-config.sh into the environment, and runs
each skill's tick.py. Errors in individual skills are caught and logged —
one broken skill never crashes the whole tick run.

Usage:
  python3 scripts/skill-scheduler.py --trigger cron
  python3 scripts/skill-scheduler.py --trigger session-open
  python3 scripts/skill-scheduler.py --trigger event --event-type home-assistant
  python3 scripts/skill-scheduler.py --list          (show all skill-lore contracts)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR        = Path(__file__).parent.parent
SKILL_LORE      = BASE_DIR / "skill-lore"
CONFIG_FILE     = BASE_DIR / "scripts" / "enchantify-config.sh"
TICK_QUEUE      = BASE_DIR / "memory" / "tick-queue.md"
LOG_FILE        = BASE_DIR / "logs" / "skill-scheduler.log"
ACTIVITY_FILE   = BASE_DIR / "config" / "skill-lore-activity.json"


# ── Config loading ────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Source enchantify-config.sh and return its exports as a dict."""
    if not CONFIG_FILE.exists():
        return {}
    result = subprocess.run(
        ["bash", "-c", f"source {CONFIG_FILE} && env"],
        capture_output=True, text=True
    )
    env = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            if key.startswith("ENCHANTIFY_"):
                env[key] = val
    return env


# ── Manifest parsing ──────────────────────────────────────────────────────────

def parse_manifest(path: Path) -> dict:
    """Extract YAML frontmatter fields from a manifest.md."""
    text = path.read_text()
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}

    manifest = {}
    block = m.group(1)

    # Simple key: value parsing (handles strings and lists)
    for line in block.splitlines():
        line = line.strip()
        if ":" in line and not line.startswith("-"):
            key, _, val = line.partition(":")
            manifest[key.strip()] = val.strip().strip('"').strip("'")

    # Extract triggers as a list of dicts
    triggers = []
    in_triggers = False
    current_trigger = {}
    for line in block.splitlines():
        if line.strip() == "triggers:":
            in_triggers = True
            continue
        if in_triggers:
            if line.startswith("  - type:"):
                if current_trigger:
                    triggers.append(current_trigger)
                current_trigger = {"type": line.split("type:")[-1].strip()}
            elif line.startswith("    schedule:"):
                current_trigger["schedule"] = line.split("schedule:")[-1].strip().strip('"')
            elif line.startswith("    event-type:"):
                current_trigger["event-type"] = line.split("event-type:")[-1].strip()
            elif line and not line.startswith(" "):
                in_triggers = False
                if current_trigger:
                    triggers.append(current_trigger)
                current_trigger = {}
    if current_trigger:
        triggers.append(current_trigger)

    manifest["triggers"] = triggers
    return manifest


def discover_skills(trigger_type: str, event_type: str = None) -> list[dict]:
    """Find all skill-lore contracts matching a trigger type."""
    skills = []
    if not SKILL_LORE.exists():
        return skills

    for manifest_path in sorted(SKILL_LORE.glob("*/manifest.md")):
        skill_dir = manifest_path.parent
        if skill_dir.name.startswith("_"):
            continue  # skip _template

        tick_script = skill_dir / "tick.py"
        if not tick_script.exists():
            continue  # no background pipeline for this skill — interactive only

        manifest = parse_manifest(manifest_path)
        if not manifest:
            continue

        for trigger in manifest.get("triggers", []):
            if trigger.get("type") == trigger_type:
                if trigger_type == "event" and event_type:
                    if trigger.get("event-type") != event_type:
                        continue
                skills.append({
                    "id":       manifest.get("id", skill_dir.name),
                    "name":     manifest.get("name", skill_dir.name),
                    "dir":      skill_dir,
                    "script":   tick_script,
                    "trigger":  trigger,
                })
                break

    return skills


# ── Runner ────────────────────────────────────────────────────────────────────

def run_skill(skill: dict, env: dict) -> bool:
    """Run one skill's tick.py. Returns True on success."""
    skill_env = {**os.environ, **env,
                 "ENCHANTIFY_BASE_DIR": str(BASE_DIR),
                 "ENCHANTIFY_SKILL_ID": skill["id"]}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  [{skill['id']}] Running...")

    try:
        result = subprocess.run(
            [sys.executable, str(skill["script"])],
            env=skill_env,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(skill["dir"])
        )

        if result.stdout:
            for line in result.stdout.strip().splitlines():
                print(f"    {line}")

        if result.stderr:
            for line in result.stderr.strip().splitlines():
                print(f"    ⚠  {line}", file=sys.stderr)

        # Log to skill-scheduler.log
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            status = "OK" if result.returncode == 0 else f"EXIT {result.returncode}"
            f.write(f"{timestamp} [{skill['id']}] {status}\n")
            if result.stderr:
                f.write(f"{timestamp} [{skill['id']}] STDERR: {result.stderr[:200]}\n")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"    ⚠  Timed out after 60s", file=sys.stderr)
        return False
    except Exception as e:
        print(f"    ⚠  Error: {e}", file=sys.stderr)
        return False


# ── List ──────────────────────────────────────────────────────────────────────

def list_skills() -> None:
    """Print all discovered skill-lore contracts."""
    if not SKILL_LORE.exists():
        print("  No skill-lore/ directory found.")
        return

    print(f"\n  Skill-lore contracts in {SKILL_LORE.relative_to(BASE_DIR)}/\n")
    for manifest_path in sorted(SKILL_LORE.glob("*/manifest.md")):
        skill_dir = manifest_path.parent
        if skill_dir.name.startswith("_"):
            continue
        manifest = parse_manifest(manifest_path)
        has_tick = (skill_dir / "tick.py").exists()
        has_lore = (skill_dir / "lore.md").exists()
        triggers = [t.get("type", "?") for t in manifest.get("triggers", [])]
        print(f"  {manifest.get('id', skill_dir.name):20s}  "
              f"{'tick ' if has_tick else '     '}"
              f"{'lore ' if has_lore else '     '}"
              f"{', '.join(triggers) or 'no triggers'}")

    print(f"\n  Run with --trigger cron|session-open|event")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run skill-lore tick scripts by trigger type")
    parser.add_argument("--trigger", choices=["cron", "session-open", "event"],
                        help="Trigger type to run")
    parser.add_argument("--event-type", default=None,
                        help="For --trigger event: the specific event type")
    parser.add_argument("--list", action="store_true",
                        help="List all skill-lore contracts and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would run without running anything")
    args = parser.parse_args()

    if args.list:
        list_skills()
        return

    if not args.trigger:
        parser.error("--trigger is required (or use --list)")

    env = load_config()
    skills = discover_skills(args.trigger, args.event_type)

    if not skills:
        print(f"  No skill-lore contracts found for trigger: {args.trigger}")
        return

    print(f"\n  skill-scheduler — trigger: {args.trigger}"
          f"{f' ({args.event_type})' if args.event_type else ''}")
    print(f"  Found {len(skills)} skill(s)\n")

    ok = 0
    for skill in skills:
        if args.dry_run:
            print(f"  [dry-run] Would run: {skill['id']} ({skill['script'].name})")
            ok += 1
        else:
            if run_skill(skill, env):
                ok += 1

    print(f"\n  Done: {ok}/{len(skills)} succeeded.")


if __name__ == "__main__":
    main()
