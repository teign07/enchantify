#!/usr/bin/env python3
"""
spend.py — The Labyrinth's real-world spending system.

The Labyrinth earns a monthly budget through player engagement. Characters
propose spending it on real things — books, coffee, donations, small gifts.
Player approves via Telegram or session conversation.

Budget: $20/month hard cap. Resets on the 1st of each month.
Card: Privacy.com virtual card. Store last 4 digits in config/secrets.env
      as LABYRINTH_CARD_LAST4 (display only — never store full card number).

Earning rates:
  Compass Run completed:     $2.00
  Enchantment cast:          $1.00
  Session completed:         $0.50
  Belief threshold crossed:  $1.00  (on crossing 25, 50, 75)

Pre-approved categories (no approval needed if amount ≤ cap and funds available):
  book: $12   coffee/tea: $8   donation: $5   delivery: $8

Usage:
  python3 scripts/spend.py --status
  python3 scripts/spend.py --earn 2.00 "Compass Run completed"
  python3 scripts/spend.py --earn-session         # $0.50 + counts from events
  python3 scripts/spend.py --propose "Zara Finch" "The Neverending Story" 8.50 book \\
      "you mentioned wanting it" --url https://bookshop.org/...
  python3 scripts/spend.py --approve abc123
  python3 scripts/spend.py --reject abc123
  python3 scripts/spend.py --execute abc123
  python3 scripts/spend.py --reset-month          # run on 1st via cron
  python3 scripts/spend.py --dry-run --status
"""

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

BASE         = Path(__file__).parent.parent
LEDGER_F     = BASE / "config" / "spend-ledger.json"
CONSENT_F    = BASE / "config" / "spend-consent.json"
SECRETS_F    = BASE / "config" / "secrets.env"
OPENCLAW_BIN = shutil.which("openclaw") or "/opt/homebrew/bin/openclaw"

_TELEGRAM_TARGET  = "8729557865"
_TELEGRAM_CHANNEL = "telegram"
_TELEGRAM_ACCOUNT = "enchantify"

MONTHLY_CAP = 20.00

EARN_RATES = {
    "compass_run":      2.00,
    "enchantment":      1.00,
    "session":          0.50,
    "belief_threshold": 1.00,
}

DEFAULT_CONSENT = {
    "pre_approved": {
        "book":     12.00,
        "coffee":    8.00,
        "tea":       8.00,
        "donation":  5.00,
        "delivery":  8.00,
    },
    "per_transaction_cap": 15.00,
    "approval_timeout_hours": 24,
    "enabled": True,
}

# ── Ledger ─────────────────────────────────────────────────────────────────────

def _new_ledger(month_str: str) -> dict:
    return {
        "current_month": month_str,
        "monthly_cap":   MONTHLY_CAP,
        "earned":        0.0,
        "spent":         0.0,
        "earnings":      [],
        "proposals":     [],
    }


def load_ledger() -> dict:
    month_str = date.today().strftime("%Y-%m")
    if LEDGER_F.exists():
        data = json.loads(LEDGER_F.read_text())
        if data.get("current_month") != month_str:
            # New month — archive old proposals, reset balance
            old = data.copy()
            data = _new_ledger(month_str)
            # Carry forward any approved-but-unexecuted proposals
            data["proposals"] = [
                p for p in old.get("proposals", [])
                if p["status"] in ("approved",)
            ]
        return data
    return _new_ledger(month_str)


def save_ledger(data: dict, dry_run: bool = False):
    if dry_run:
        return
    LEDGER_F.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_F.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def available_balance(data: dict) -> float:
    earned_cap = min(data["earned"], data["monthly_cap"])
    pending = sum(
        p["amount"] for p in data["proposals"]
        if p["status"] in ("pending", "approved")
    )
    return max(0.0, round(earned_cap - data["spent"] - pending, 2))


# ── Consent ────────────────────────────────────────────────────────────────────

def load_consent() -> dict:
    if CONSENT_F.exists():
        return json.loads(CONSENT_F.read_text())
    return DEFAULT_CONSENT


def is_pre_approved(category: str, amount: float, consent: dict) -> bool:
    if not consent.get("enabled", True):
        return False
    cap = consent.get("pre_approved", {}).get(category.lower())
    if cap is None:
        return False
    return amount <= cap


# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    if SECRETS_F.exists():
        for line in SECRETS_F.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


# ── Telegram ───────────────────────────────────────────────────────────────────

def send_telegram(text: str):
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    result = subprocess.run(
        [OPENCLAW_BIN, "message", "send",
         "--target",  _TELEGRAM_TARGET,
         "--channel", _TELEGRAM_CHANNEL,
         "--account", _TELEGRAM_ACCOUNT,
         "-m", text],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ⚠ Telegram send failed: {result.stderr.strip()[:100]}")


# ── Core actions ───────────────────────────────────────────────────────────────

def earn(amount: float, reason: str, dry_run: bool = False) -> float:
    """Add to monthly balance. Returns new available balance."""
    data = load_ledger()
    before = available_balance(data)

    data["earned"] = round(data["earned"] + amount, 2)
    data["earnings"].append({
        "date":   date.today().isoformat(),
        "amount": amount,
        "reason": reason,
    })

    save_ledger(data, dry_run)
    after = available_balance(data)

    cap_str = ""
    if data["earned"] >= data["monthly_cap"]:
        cap_str = " (monthly cap reached)"
    print(f"  + ${amount:.2f} earned — {reason}{cap_str}")
    print(f"    Balance: ${before:.2f} → ${after:.2f} available")
    return after


def propose(
    character: str,
    item: str,
    amount: float,
    category: str,
    reason: str,
    url: str = "",
    dry_run: bool = False,
) -> str:
    """Create a spend proposal. Auto-approves if pre-approved category and funds available."""
    data    = load_ledger()
    consent = load_consent()
    cfg     = load_config()
    card    = cfg.get("LABYRINTH_CARD_LAST4", "****")

    if not consent.get("enabled", True):
        print("  ⚠ Spending system is disabled in consent config.")
        return ""

    per_cap = consent.get("per_transaction_cap", 15.00)
    if amount > per_cap:
        print(f"  ⚠ Amount ${amount:.2f} exceeds per-transaction cap ${per_cap:.2f}.")
        return ""

    avail = available_balance(data)
    if amount > avail:
        print(f"  ⚠ Insufficient balance. Available: ${avail:.2f}, requested: ${amount:.2f}.")
        return ""

    proposal_id = uuid.uuid4().hex[:8]
    auto = is_pre_approved(category, amount, consent) and amount <= avail
    status = "approved" if auto else "pending"

    proposal = {
        "id":          proposal_id,
        "character":   character,
        "item":        item,
        "url":         url,
        "amount":      amount,
        "category":    category,
        "reason":      reason,
        "status":      status,
        "proposed_at": datetime.now().isoformat(),
        "approved_at": datetime.now().isoformat() if auto else None,
        "executed_at": None,
    }

    if not dry_run:
        data["proposals"].append(proposal)
        save_ledger(data)

    if auto:
        print(f"  ✓ Proposal {proposal_id} auto-approved ({category}, ${amount:.2f}).")
        url_line = f"\n🔗 {url}" if url else ""
        msg = (
            f"📦 <b>{character}</b> wants to send you something.\n\n"
            f"<i>{item}</i> — ${amount:.2f}\n"
            f"<i>{reason}</i>{url_line}\n\n"
            f"Pre-approved. Use your Labyrinth card (·{card}) when ready.\n"
            f"<code>python3 scripts/spend.py --execute {proposal_id}</code>"
        )
        if not dry_run:
            send_telegram(msg)
    else:
        print(f"  · Proposal {proposal_id} pending approval.")
        url_line = f"\n🔗 {url}" if url else ""
        msg = (
            f"📦 <b>{character}</b> wants to send you something.\n\n"
            f"<i>{item}</i> — ${amount:.2f}\n"
            f"<i>{reason}</i>{url_line}\n\n"
            f"Available this month: ${avail:.2f}\n\n"
            f"To approve: <code>python3 scripts/spend.py --approve {proposal_id}</code>\n"
            f"To reject:  <code>python3 scripts/spend.py --reject {proposal_id}</code>"
        )
        if not dry_run:
            send_telegram(msg)

    return proposal_id


def _find_proposal(data: dict, proposal_id: str) -> Optional[dict]:
    for p in data["proposals"]:
        if p["id"] == proposal_id:
            return p
    return None


def approve(proposal_id: str, dry_run: bool = False):
    data = load_ledger()
    p = _find_proposal(data, proposal_id)
    if not p:
        print(f"  ✗ Proposal {proposal_id} not found.")
        return
    if p["status"] != "pending":
        print(f"  · Proposal {proposal_id} is already {p['status']}.")
        return

    p["status"]      = "approved"
    p["approved_at"] = datetime.now().isoformat()
    save_ledger(data, dry_run)

    cfg  = load_config()
    card = cfg.get("LABYRINTH_CARD_LAST4", "****")
    url_line = f"\n🔗 {p['url']}" if p.get("url") else ""
    msg = (
        f"✅ Approved — <b>{p['character']}</b>: <i>{p['item']}</i> (${p['amount']:.2f}){url_line}\n\n"
        f"Use your Labyrinth card (·{card}) when ready.\n"
        f"<code>python3 scripts/spend.py --execute {proposal_id}</code>"
    )
    if not dry_run:
        send_telegram(msg)
    print(f"  ✓ Proposal {proposal_id} approved.")


def reject(proposal_id: str, dry_run: bool = False):
    data = load_ledger()
    p = _find_proposal(data, proposal_id)
    if not p:
        print(f"  ✗ Proposal {proposal_id} not found.")
        return
    if p["status"] not in ("pending", "approved"):
        print(f"  · Proposal {proposal_id} is already {p['status']}.")
        return

    p["status"] = "rejected"
    save_ledger(data, dry_run)
    print(f"  · Proposal {proposal_id} rejected.")


def execute(proposal_id: str, dry_run: bool = False):
    data = load_ledger()
    p = _find_proposal(data, proposal_id)
    if not p:
        print(f"  ✗ Proposal {proposal_id} not found.")
        return
    if p["status"] != "approved":
        print(f"  ✗ Proposal {proposal_id} must be approved before executing (status: {p['status']}).")
        return

    p["status"]      = "executed"
    p["executed_at"] = datetime.now().isoformat()
    data["spent"]    = round(data["spent"] + p["amount"], 2)
    save_ledger(data, dry_run)

    msg = (
        f"📬 <b>{p['character']}</b> sent you something.\n\n"
        f"<i>{p['item']}</i> — ${p['amount']:.2f} spent.\n"
        f"<i>{p['reason']}</i>\n\n"
        f"Monthly balance: ${available_balance(data):.2f} remaining."
    )
    if not dry_run:
        send_telegram(msg)
    print(f"  ✓ Executed. ${p['amount']:.2f} deducted. Balance: ${available_balance(data):.2f}")


def reset_month(dry_run: bool = False):
    """Archive old ledger and start fresh. Called by cron on the 1st."""
    data = load_ledger()
    month = data.get("current_month", "?")

    # Archive
    archive_path = BASE / "config" / f"spend-ledger-{month}.json"
    if not dry_run and LEDGER_F.exists():
        LEDGER_F.rename(archive_path)
        print(f"  ✓ Archived {month} ledger → {archive_path.name}")

    new_month = date.today().strftime("%Y-%m")
    fresh = _new_ledger(new_month)
    save_ledger(fresh, dry_run)

    msg = (
        f"💳 New month, new budget.\n\n"
        f"The Labyrinth's spending account has reset.\n"
        f"Available: $0.00 — earn it back through Compass Runs and Enchantments."
    )
    if not dry_run:
        send_telegram(msg)
    print(f"  ✓ Month reset to {new_month}. Fresh $0.00 balance.")


# ── Status display ─────────────────────────────────────────────────────────────

def status():
    data    = load_ledger()
    consent = load_consent()
    cfg     = load_config()
    card    = cfg.get("LABYRINTH_CARD_LAST4", "(not configured)")
    avail   = available_balance(data)
    earned_capped = min(data["earned"], data["monthly_cap"])

    print(f"\n💳 Labyrinth Spending — {data['current_month']}")
    print(f"   Card: ·{card}")
    print(f"   Earned:    ${data['earned']:.2f}  (cap: ${data['monthly_cap']:.2f})")
    print(f"   Spent:     ${data['spent']:.2f}")
    pending_amt = sum(p["amount"] for p in data["proposals"] if p["status"] in ("pending","approved"))
    if pending_amt:
        print(f"   Pending:   ${pending_amt:.2f}")
    print(f"   Available: ${avail:.2f}")

    if not consent.get("enabled", True):
        print("   ⚠ Spending disabled in consent config.")

    recent_earnings = data["earnings"][-5:]
    if recent_earnings:
        print("\n   Recent earnings:")
        for e in recent_earnings:
            print(f"     + ${e['amount']:.2f}  {e['reason']}  ({e['date']})")

    active = [p for p in data["proposals"] if p["status"] in ("pending","approved")]
    if active:
        print("\n   Pending proposals:")
        for p in active:
            url_hint = " 🔗" if p.get("url") else ""
            print(f"     [{p['id']}] {p['character']}: {p['item']} — ${p['amount']:.2f} ({p['status']}){url_hint}")
            print(f"       Approve: python3 scripts/spend.py --approve {p['id']}")

    recent_executed = [p for p in data["proposals"] if p["status"] == "executed"][-3:]
    if recent_executed:
        print("\n   Recently sent:")
        for p in recent_executed:
            print(f"     ✓ {p['character']}: {p['item']} — ${p['amount']:.2f}")

    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Labyrinth real-world spending system")
    parser.add_argument("--status",       action="store_true")
    parser.add_argument("--earn",         nargs=2, metavar=("AMOUNT", "REASON"))
    parser.add_argument("--earn-session", action="store_true",
                        help="Award $0.50 for session completion")
    parser.add_argument("--propose",      nargs=5,
                        metavar=("CHARACTER", "ITEM", "AMOUNT", "CATEGORY", "REASON"))
    parser.add_argument("--url",          default="", help="URL for the item (used with --propose)")
    parser.add_argument("--approve",      metavar="ID")
    parser.add_argument("--reject",       metavar="ID")
    parser.add_argument("--execute",      metavar="ID")
    parser.add_argument("--reset-month",  action="store_true")
    parser.add_argument("--dry-run",      action="store_true")
    args = parser.parse_args()

    if args.status or len(sys.argv) == 1:
        status()

    elif args.earn:
        amount = float(args.earn[0])
        reason = args.earn[1]
        earn(amount, reason, args.dry_run)

    elif args.earn_session:
        earn(EARN_RATES["session"], "Session completed", args.dry_run)

    elif args.propose:
        character, item, amount_str, category, reason = args.propose
        propose(character, item, float(amount_str), category, reason,
                url=args.url, dry_run=args.dry_run)

    elif args.approve:
        approve(args.approve, args.dry_run)

    elif args.reject:
        reject(args.reject, args.dry_run)

    elif args.execute:
        execute(args.execute, args.dry_run)

    elif args.reset_month:
        reset_month(args.dry_run)


if __name__ == "__main__":
    main()
