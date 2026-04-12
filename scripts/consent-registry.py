#!/usr/bin/env python3
"""
consent-registry.py — Read and update the Enchantify consent registry.

Usage:
  python3 scripts/consent-registry.py check <action_id>
  python3 scripts/consent-registry.py list
  python3 scripts/consent-registry.py approve <action_id>
  python3 scripts/consent-registry.py revoke <action_id>
  python3 scripts/consent-registry.py pact-activate <pact_id>
  python3 scripts/consent-registry.py pact-deactivate <pact_id>

Returns exit code 0 if approved, 1 if not approved or error.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR     = Path(__file__).parent.parent
CONSENT_PATH = BASE_DIR / "config" / "consent.json"


def load() -> dict:
    if not CONSENT_PATH.exists():
        print("consent.json not found", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONSENT_PATH.read_text())


def save(data: dict) -> None:
    CONSENT_PATH.write_text(json.dumps(data, indent=2))


def is_approved(data: dict, action_id: str) -> bool:
    action = data.get("actions", {}).get(action_id)
    if action is None:
        return False
    return bool(action.get("approved", False))


def check(action_id: str) -> int:
    data = load()
    approved = is_approved(data, action_id)
    scope    = data.get("actions", {}).get(action_id, {}).get("scope", "unknown")
    desc     = data.get("actions", {}).get(action_id, {}).get("description", "")
    status   = "APPROVED" if approved else "NOT APPROVED"
    print(f"{action_id}: {status} (scope: {scope}) — {desc}")
    return 0 if approved else 1


def list_all() -> None:
    data    = load()
    actions = data.get("actions", {})

    print("\n== Enchantify Consent Registry ==\n")
    print(f"{'Action':<30} {'Scope':<15} {'Approved':<10} Description")
    print("-" * 80)
    for action_id, cfg in sorted(actions.items()):
        approved = "✓" if cfg.get("approved") else "✗"
        scope    = cfg.get("scope", "?")
        desc     = cfg.get("description", "")
        print(f"{action_id:<30} {scope:<15} {approved:<10} {desc}")

    print("\n== Active Pacts ==\n")
    pacts = data.get("pacts", {})
    for pact_id, cfg in sorted(pacts.items()):
        active  = "✓ active" if cfg.get("active") else "✗ inactive"
        governs = ", ".join(cfg.get("governs", []))
        print(f"  {pact_id}: {active}")
        print(f"    governs: {governs}")

    override = data.get("emergency_override", "?")
    print(f"\n  Emergency override word: {override}")
    print()


def approve(action_id: str) -> None:
    data = load()
    if action_id not in data.get("actions", {}):
        print(f"Unknown action: {action_id}", file=sys.stderr)
        sys.exit(1)
    data["actions"][action_id]["approved"] = True
    save(data)
    print(f"Approved: {action_id}")


def revoke(action_id: str) -> None:
    data = load()
    if action_id not in data.get("actions", {}):
        print(f"Unknown action: {action_id}", file=sys.stderr)
        sys.exit(1)
    data["actions"][action_id]["approved"] = False
    save(data)
    print(f"Revoked: {action_id}")


def pact_activate(pact_id: str) -> None:
    data = load()
    if pact_id not in data.get("pacts", {}):
        data.setdefault("pacts", {})[pact_id] = {"active": True, "activated_at": None, "governs": []}
    data["pacts"][pact_id]["active"] = True
    data["pacts"][pact_id]["activated_at"] = datetime.now().isoformat()
    save(data)
    print(f"Pact activated: {pact_id}")


def pact_deactivate(pact_id: str) -> None:
    data = load()
    if pact_id not in data.get("pacts", {}):
        print(f"Unknown pact: {pact_id}", file=sys.stderr)
        sys.exit(1)
    data["pacts"][pact_id]["active"] = False
    save(data)
    print(f"Pact deactivated: {pact_id}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        list_all()
        sys.exit(0)

    cmd = args[0]

    if cmd == "check" and len(args) == 2:
        sys.exit(check(args[1]))
    elif cmd == "list":
        list_all()
    elif cmd == "approve" and len(args) == 2:
        approve(args[1])
    elif cmd == "revoke" and len(args) == 2:
        revoke(args[1])
    elif cmd == "pact-activate" and len(args) == 2:
        pact_activate(args[1])
    elif cmd == "pact-deactivate" and len(args) == 2:
        pact_deactivate(args[1])
    else:
        print(f"Usage: consent-registry.py [check|list|approve|revoke|pact-activate|pact-deactivate] [action_id|pact_id]")
        sys.exit(1)
