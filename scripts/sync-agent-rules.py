#!/usr/bin/env python3
"""Sync the lean AGENTS.md operating page into the installed OpenClaw agent."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DEFAULT_AGENT_DIR = Path.home() / ".openclaw" / "agents" / "enchantify"
LIMIT = 13_500


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync AGENTS.md to installed OpenClaw agent files")
    parser.add_argument("--agent-dir", type=Path, default=DEFAULT_AGENT_DIR)
    parser.add_argument("--limit", type=int, default=LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = BASE / "AGENTS.md"
    text = source.read_text(encoding="utf-8")
    chars = len(text)
    if chars > args.limit:
        raise SystemExit(f"Refusing to sync: AGENTS.md is {chars} chars, limit is {args.limit}")

    targets = [args.agent_dir / "agent.md", args.agent_dir / "AGENTS.md"]
    if args.dry_run:
        print(f"[dry-run] {source} ({chars} chars) -> " + ", ".join(str(t) for t in targets))
        return 0

    args.agent_dir.mkdir(parents=True, exist_ok=True)
    backup_dir = Path("/tmp/enchantify-agent-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    for target in targets:
        if target.exists():
            shutil.copy2(target, backup_dir / f"{target.name}.{stamp}.bak")
        target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        print(f"✓ Synced {target} ({chars} chars)")
    print(f"Backups: {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
