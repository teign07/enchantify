#!/usr/bin/env python3
"""
github/tick.py — Read recent GitHub activity via gh CLI and write narrative seeds.

Requires: gh CLI authenticated (gh auth login)
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR   = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent.parent))
SKILL_ID   = os.environ.get("ENCHANTIFY_SKILL_ID", "github")
TICK_QUEUE = BASE_DIR / "memory" / "tick-queue.md"

GH_USER  = os.environ.get("ENCHANTIFY_GITHUB_USERNAME", "")
GH_REPOS = os.environ.get("ENCHANTIFY_GITHUB_REPOS", "")

if not GH_USER:
    print(f"[{SKILL_ID}] Missing config: ENCHANTIFY_GITHUB_USERNAME", file=sys.stderr)
    sys.exit(0)


def gh(cmd: str) -> list | dict | None:
    try:
        result = subprocess.run(
            f"gh {cmd}",
            shell=True, capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def get_recent_commits() -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    if GH_REPOS:
        repos = [r.strip() for r in GH_REPOS.split(",") if r.strip()]
    else:
        data = gh(f"repo list {GH_USER} --limit 20 --json nameWithOwner")
        if not data:
            return []
        repos = [r["nameWithOwner"] for r in data]

    commits = []
    for repo in repos[:5]:  # cap to avoid rate limits
        data = gh(f"api repos/{repo}/commits?author={GH_USER}&since={since}&per_page=10")
        if not data or not isinstance(data, list):
            continue
        for c in data:
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            commits.append({"repo": repo, "message": msg})

    return commits


def get_pr_activity() -> list[dict]:
    data = gh(f"pr list --author {GH_USER} --state all --limit 5 --json title,state,mergedAt,createdAt")
    if not data:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    recent = []
    for pr in data:
        for date_field in ["mergedAt", "createdAt"]:
            if pr.get(date_field):
                try:
                    dt = datetime.fromisoformat(pr[date_field].replace("Z", "+00:00"))
                    if dt > cutoff:
                        recent.append({"title": pr["title"], "state": pr["state"]})
                        break
                except Exception:
                    pass
    return recent


def fetch() -> list[dict]:
    items = []

    commits = get_recent_commits()
    prs     = get_pr_activity()

    if len(commits) >= 5:
        messages = "; ".join(f"\"{c['message']}\"" for c in commits[:3])
        items.append({
            "raw":  f"{len(commits)} commits yesterday: {messages}, and {len(commits)-3} more",
            "seed": f"A deep session in the Ink Well — {len(commits)} entries, sustained focus.",
        })
    elif len(commits) > 0:
        msg = commits[0]["message"]
        items.append({
            "raw":  f"{len(commits)} commit(s): \"{msg}\"",
            "seed": f"The Ink Well received new entries: \"{msg}.\"",
        })

    for pr in prs[:2]:
        title = pr["title"]
        state = pr["state"]
        if state == "MERGED":
            seed = f"A manuscript was accepted into the canon: \"{title}.\""
        elif state == "OPEN":
            seed = f"A manuscript is under review, awaiting other voices: \"{title}.\""
        else:
            seed = f"A manuscript was withdrawn: \"{title}.\""
        items.append({"raw": f"PR {state}: \"{title}\"", "seed": seed})

    return items[:4]


def write_to_queue(items: list[dict]) -> None:
    if not items:
        print(f"[{SKILL_ID}] No recent GitHub activity.")
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
