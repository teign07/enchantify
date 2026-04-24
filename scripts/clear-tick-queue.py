#!/usr/bin/env python3
"""
clear-tick-queue.py — Reset memory/tick-queue.md after session open reads it.

Called at session open after the Labyrinth reads and incorporates tick results.

Usage:
  python3 scripts/clear-tick-queue.py
"""
from pathlib import Path
from tick_queue_utils import ensure_header

QUEUE = Path(__file__).parent.parent / "memory" / "tick-queue.md"

HEADER = (
    "# Tick Queue\n\n"
    "*Entities stirred by simulation between sessions. "
    "Read at session open, then cleared.*\n"
)

ensure_header(QUEUE, HEADER)
QUEUE.write_text(HEADER)
print(f"✓ Tick queue cleared.")
