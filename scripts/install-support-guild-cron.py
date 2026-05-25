#!/usr/bin/env python3
"""Install the modern Enchantify cron set.

Kept as a compatibility wrapper for older docs/commands.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    proc = subprocess.run([sys.executable, str(base / "scripts" / "install-crons.py"), "--player", "bj"])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
