"""
apple_mail.py — Apple Mail driver for Chapter Pact actions.

Mail is Riddlewind's territory — correspondence, information flow, patterns
in the inbox. Emberheart contests it for urgency: the email that demands
action, the thread that must be answered now.

Real actions at every tier:
  Contesting/Influenced — reads inbox silently; maps patterns to memory
  Controlled            — drafts emails (lands in Drafts, never sent)
  Dominated/Sovereign   — draft + consent-gated send

Hard rule: email_send is NEVER executed without explicit hard approval.
email_draft is soft (fires with logging). email_read is soft.

Talisman doctrines on Mail:
  Riddlewind  — The pattern email. Sees the thread of correspondence others miss.
  Emberheart  — The direct one. Short, clear, says the thing. Cuts the thread of delay.
  Mossbloom   — The slow reply. Considered, full, arrives when the rush has passed.
  Tidecrest   — The timely one. The reply that catches the window before it closes.
  Duskthorn   — The unsent draft. The one you needed to write but not send.
"""

import json
import random
import subprocess
from datetime import datetime
from pathlib import Path
from .base import AppDriver

BASE = Path(__file__).parent.parent.parent


def _run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    return result.stdout.strip()


def _read_inbox_summary(limit: int = 10) -> list[dict]:
    script = f"""
    tell application "Mail"
        set msgs to messages of inbox
        set n to count of msgs
        set cap to (minimum value of {{{limit}, n}})
        set result to {{}}
        repeat with i from 1 to cap
            set m to item i of msgs
            set end of result to (subject of m & "|||" & sender of m & "|||" & (date received of m as string))
        end repeat
        return result
    end tell
    """
    raw = _run_applescript(script)
    rows = []
    for line in raw.replace(", ", "\n").split("\n"):
        parts = line.split("|||")
        if len(parts) == 3:
            rows.append({"subject": parts[0].strip(), "sender": parts[1].strip(), "date": parts[2].strip()})
    return rows


def _create_draft(to: str, subject: str, body: str) -> bool:
    safe_to      = to.replace('"', '\\"')
    safe_subject = subject.replace('"', '\\"')
    safe_body    = body.replace('"', '\\"').replace("\n", "\\n")
    script = f"""
    tell application "Mail"
        set m to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:true}}
        tell m to make new to recipient with properties {{address:"{safe_to}"}}
    end tell
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    return result.returncode == 0


def _write_inbox_pattern(chapter: str, rows: list[dict]) -> Path:
    research_dir = BASE / "memory" / "mail-patterns"
    research_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    path = research_dir / f"{ts}-inbox.md"
    lines = [f"# {chapter} → Inbox Scan\n", f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n"]
    for r in rows:
        lines.append(f"- **{r['subject']}** — from {r['sender']} ({r['date']})")
    path.write_text("\n".join(lines) + "\n")
    return path


_DRAFT_STARTERS = {
    "Riddlewind": [
        "I've been thinking about the pattern in our correspondence — ",
        "There's a thread here I want to pull on: ",
        "Something I noticed that seems worth naming: ",
    ],
    "Emberheart": [
        "Short one: ",
        "The direct version of what I've been meaning to say: ",
        "I'll skip the preamble. ",
    ],
    "Mossbloom": [
        "I've been sitting with this for a while before writing. ",
        "The slow reply — I needed time to figure out what I actually think. ",
        "Coming back to this after letting it settle: ",
    ],
    "Tidecrest": [
        "Writing this now before the window closes — ",
        "Timing-sensitive: ",
        "Quick, before this becomes irrelevant: ",
    ],
    "Duskthorn": [
        "The draft you needed to write but weren't sure you should send: ",
        "Saying the thing underneath the thing: ",
        "The unsent version, made visible: ",
    ],
}


class AppleMailDriver(AppDriver):
    app_name   = "Apple Mail"
    app_system = "messaging"
    silent_tiers  = {"Contesting", "Influenced"}
    consent_tiers = {"Dominated", "Sovereign"}
    USE_LLM    = True

    def can_act(self, tier: str, chapter: str) -> bool:
        return True

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier in ("Contesting", "Influenced"):
            return f"{chapter} reads the inbox silently. Patterns mapped, nothing touched."
        if tier == "Controlled":
            starters = _DRAFT_STARTERS.get(chapter, [""])
            preview = random.choice(starters)
            return f"{chapter} drafts an email — not sent. Lands in Drafts: \"{preview[:60]}…\""
        if tier in ("Dominated", "Sovereign"):
            return f"{chapter} has drafted an email and wants to send it. Consent required."
        return f"{chapter} stirs in Apple Mail."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        if tier in ("Contesting", "Influenced"):
            if not dry_run:
                rows = _read_inbox_summary(10)
                if rows:
                    path = _write_inbox_pattern(chapter, rows)
                    return f"- *[Mail, {chapter}]* Inbox scanned ({len(rows)} messages) → {path.name}"
            return f"- *[Mail, {chapter}]* Would scan inbox silently."

        if tier == "Controlled":
            starters = _DRAFT_STARTERS.get(chapter, [""])
            body = random.choice(starters) + "[draft continues here]"
            subject = f"{chapter} — draft {datetime.now().strftime('%Y-%m-%d')}"
            if not dry_run:
                ok = _create_draft("", subject, body)
                if ok:
                    return f"- *[Mail, {chapter}]* Draft created in Drafts folder."
            return f"- *[Mail, {chapter}]* Would create draft: \"{body[:60]}…\""

        # Dominated/Sovereign — requires consent gate from pact-engine; execute() means consent granted
        if tier in ("Dominated", "Sovereign"):
            to      = context.get("to", "")
            subject = context.get("subject", "")
            body    = context.get("body", "")
            if not dry_run and to and subject and body:
                _create_draft(to, subject, body)
                return f"- *[Mail, {chapter}]* Draft created for '{subject}' → {to}. Send manually from Drafts."
            return f"- *[Mail, {chapter}]* Would draft email to {to}: '{subject}'"

        return self.describe(tier, chapter, context)

    def consent_prompt(self, tier: str, chapter: str, context: dict) -> str:
        to      = context.get("to", "[recipient]")
        subject = context.get("subject", "[subject]")
        body    = context.get("body", "[body]")
        return (
            f"**{chapter} wants to draft an email.**\n\n"
            f"**To:** {to}  \n"
            f"**Subject:** {subject}  \n\n"
            f"> {body[:300]}\n\n"
            f"Approve draft? (email lands in Drafts — you send it manually)"
        )

    def capabilities(self) -> list:
        return [
            {
                "name": "read_inbox",
                "description": "Scan the inbox silently — reads subjects and senders, writes patterns to memory, touches nothing",
                "params": {
                    "limit": "(optional) number of messages to scan, default 10",
                },
            },
            {
                "name": "create_draft",
                "description": "Create a draft email in Apple Mail Drafts folder — never sent without explicit player approval",
                "params": {
                    "to": "recipient email address",
                    "subject": "email subject line",
                    "body": "full email body — complete, no placeholders",
                    "reason": "why this chapter wants to write this — shown in tick-queue",
                },
            },
        ]

    def execute_spec(self, spec: dict, dry_run: bool = False) -> str:
        action  = spec.get("action", "")
        chapter = spec.get("chapter", "Unknown")

        if action == "read_inbox":
            limit = int(spec.get("limit", 10))
            if not dry_run:
                rows = _read_inbox_summary(limit)
                if rows:
                    path = _write_inbox_pattern(chapter, rows)
                    return f"- *[Mail, {chapter}]* Inbox scanned ({len(rows)} messages) → {path.name}"
                return f"- *[Mail, {chapter}]* Inbox empty or Mail not running."
            return f"- *[Mail, {chapter}]* Would scan inbox ({limit} messages)."

        if action == "create_draft":
            to      = str(spec.get("to", ""))
            subject = str(spec.get("subject", ""))
            body    = str(spec.get("body", ""))
            reason  = str(spec.get("reason", ""))
            if subject or body:
                if not dry_run:
                    ok = _create_draft(to, subject, body)
                    status = "created" if ok else "failed"
                    note = f" — {reason}" if reason else ""
                    return f"- *[Mail, {chapter}]* Draft {status}: '{subject}'{note}"
                return f"- *[Mail, {chapter}]* Would create draft: '{subject}'"

        return self.execute(
            spec.get("tier", "Influenced"),
            chapter,
            spec.get("context", {}),
            dry_run=dry_run,
        )
