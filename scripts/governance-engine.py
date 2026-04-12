#!/usr/bin/env python3
"""
governance-engine.py — The Narrative OS pact executor.

Reads active pacts from pacts/*/manifest.md, evaluates trigger conditions,
checks consent, calls action modules, logs everything to action-chronicle.md.

Usage:
  python3 scripts/governance-engine.py --trigger session-open
  python3 scripts/governance-engine.py --trigger compass-direction --context north
  python3 scripts/governance-engine.py --trigger nothing-encounter
  python3 scripts/governance-engine.py --trigger belief-gained --context 9
  python3 scripts/governance-engine.py --trigger ambient-state
  python3 scripts/governance-engine.py --list

The Labyrinth calls this during sessions. The 4-hour cron calls --trigger ambient-state.
"""
import importlib.util
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

BASE_DIR     = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent))
CONSENT_PATH = BASE_DIR / "config" / "consent.json"
CHRONICLE    = BASE_DIR / "logs" / "action-chronicle.md"
PACTS_DIR    = BASE_DIR / "pacts"

# Add BASE_DIR to path so action modules can be imported
sys.path.insert(0, str(BASE_DIR))


# ─── Load consent ────────────────────────────────────────────────────────────

def load_consent() -> dict:
    if not CONSENT_PATH.exists():
        return {}
    return json.loads(CONSENT_PATH.read_text())


def is_approved(consent: dict, action_id: str) -> bool:
    return consent.get("actions", {}).get(action_id, {}).get("approved", False)


def is_pact_active(consent: dict, pact_id: str) -> bool:
    return consent.get("pacts", {}).get(pact_id, {}).get("active", False)


# ─── Load pact manifests ──────────────────────────────────────────────────────

def load_manifests() -> list[dict]:
    pacts = []
    if not PACTS_DIR.exists():
        return pacts

    for manifest_path in sorted(PACTS_DIR.glob("*/manifest.md")):
        pact_id = manifest_path.parent.name
        if pact_id == "_template":
            continue

        text = manifest_path.read_text()

        # Extract YAML frontmatter
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue

        yaml_text = m.group(1)
        data      = {"id": pact_id, "path": manifest_path.parent}

        for line in yaml_text.splitlines():
            kv = line.split(":", 1)
            if len(kv) == 2:
                k, v = kv[0].strip(), kv[1].strip()
                data[k] = v

        # Extract triggers list
        triggers_m = re.search(r"triggers:(.*?)(?=\n\w|\Z)", yaml_text, re.DOTALL)
        if triggers_m:
            trigger_lines = re.findall(r"- (.+)", triggers_m.group(1))
            data["triggers"] = trigger_lines
        else:
            data["triggers"] = []

        pacts.append(data)

    return pacts


# ─── Load govern module ───────────────────────────────────────────────────────

def load_govern(pact_path: Path):
    """Dynamically load a pact's govern.py and return the module."""
    govern_path = pact_path / "govern.py"
    if not govern_path.exists():
        return None

    spec   = importlib.util.spec_from_file_location("govern", govern_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"[governance] Error loading {govern_path}: {e}", file=sys.stderr)
        return None


# ─── Call action module ───────────────────────────────────────────────────────

def call_action(action_id: str, params: dict) -> dict:
    """Route an action call to the correct actions/ module."""
    module_map = {
        "spotify_":     "actions.spotify",
        "notification_": "actions.notifications",
        "do_not_disturb": "actions.notifications",
        "obsidian_":    "actions.obsidian",
        "lifx_":        None,  # handled by lifx-control.py subprocess
    }

    module_name = None
    for prefix, mod in module_map.items():
        if action_id.startswith(prefix):
            module_name = mod
            break

    # LIFX uses the existing lifx-control.py script
    if action_id.startswith("lifx_"):
        import subprocess
        scene = params.get("scene", "academy")
        result = subprocess.run(
            ["python3", str(BASE_DIR / "scripts" / "lifx-control.py"), "scene", scene],
            capture_output=True, text=True, timeout=15
        )
        ok = result.returncode == 0
        return {"success": ok, "message": f"LIFX scene: {scene}" if ok else result.stderr.strip()}

    if not module_name:
        return {"success": False, "message": f"No module for action: {action_id}"}

    try:
        module = importlib.import_module(module_name)
        return module.run(action_id, params)
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─── Chronicle ────────────────────────────────────────────────────────────────

def log_action(pact_id: str, trigger: str, action_id: str, params: dict, result: dict) -> None:
    CHRONICLE.parent.mkdir(parents=True, exist_ok=True)
    if not CHRONICLE.exists():
        CHRONICLE.write_text("# Action Chronicle\n\n*All governance engine actions. Written by governance-engine.py.*\n\n---\n")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    status    = "✓" if result.get("success") else "✗"
    msg       = result.get("message", "")

    with CHRONICLE.open("a") as f:
        f.write(f"\n## {timestamp} — {pact_id} / {trigger}\n")
        f.write(f"- Action: `{action_id}` {status}\n")
        if params:
            f.write(f"- Params: {json.dumps(params)}\n")
        if msg:
            f.write(f"- Result: {msg}\n")


# ─── Main executor ────────────────────────────────────────────────────────────

def run_trigger(trigger: str, context: str = "", dry_run: bool = False) -> None:
    consent   = load_consent()
    manifests = load_manifests()

    if not consent.get("global", {}).get("enabled", True):
        print("[governance] Governance is disabled globally. Exiting.")
        return

    fired = 0

    for pact in manifests:
        pact_id = pact["id"]

        if not is_pact_active(consent, pact_id):
            continue

        # Check if this trigger matches this pact
        pact_triggers = pact.get("triggers", [])
        trigger_match = any(
            t.strip().lower().startswith(trigger.lower())
            or trigger.lower() in t.strip().lower()
            for t in pact_triggers
        )
        if not trigger_match:
            continue

        govern = load_govern(pact["path"])
        if govern is None or not hasattr(govern, "handle"):
            continue

        try:
            actions = govern.handle(trigger=trigger, context=context)
        except Exception as e:
            print(f"[governance] {pact_id} govern.handle() error: {e}", file=sys.stderr)
            continue

        if not actions:
            continue

        for action_call in actions:
            action_id = action_call.get("action")
            params    = action_call.get("params", {})

            if not action_id:
                continue

            if not is_approved(consent, action_id):
                print(f"[governance] {pact_id}: {action_id} not approved — skipping")
                continue

            if dry_run:
                print(f"[governance] [DRY RUN] {pact_id}: would fire {action_id} {params}")
                continue

            result = call_action(action_id, params)
            status = "✓" if result.get("success") else "✗"
            print(f"[governance] {pact_id}: {action_id} {status} — {result.get('message', '')}")

            if consent.get("global", {}).get("log_all_actions", True):
                log_action(pact_id, trigger, action_id, params, result)

            fired += 1

    if fired == 0 and not dry_run:
        print(f"[governance] No actions fired for trigger: {trigger}")


def list_pacts() -> None:
    consent   = load_consent()
    manifests = load_manifests()

    print("\n== Active Pacts ==\n")
    for pact in manifests:
        pact_id = pact["id"]
        active  = "✓" if is_pact_active(consent, pact_id) else "✗"
        name    = pact.get("name", pact_id)
        chapter = pact.get("chapter", "?")
        triggers = pact.get("triggers", [])
        govern_exists = (pact["path"] / "govern.py").exists()
        print(f"  {active} {name} ({chapter})")
        print(f"    triggers: {', '.join(triggers)}")
        print(f"    govern.py: {'present' if govern_exists else 'MISSING'}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--list" in args:
        list_pacts()
        sys.exit(0)

    dry_run = "--dry-run" in args
    args    = [a for a in args if a not in ("--dry-run",)]

    trigger = ""
    context = ""

    for i, arg in enumerate(args):
        if arg == "--trigger" and i + 1 < len(args):
            trigger = args[i + 1]
        elif arg == "--context" and i + 1 < len(args):
            context = args[i + 1]

    if not trigger:
        print("Usage: governance-engine.py --trigger <type> [--context <value>] [--dry-run] [--list]")
        sys.exit(1)

    run_trigger(trigger, context, dry_run)
