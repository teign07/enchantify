#!/usr/bin/env python3
"""Backward-compatible wrapper for Enchantify's MusicGen scene cue script.

Usage:
  python3 skills/musicgen/musicgen_wrapper.py "prompt" [duration_in_seconds]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
SCENE_SCRIPT = BASE / "scripts" / "musicgen_scene.py"
DEFAULT_OUTPUT = BASE / "tmp" / "scene-outbox" / "musicgen-wrapper.wav"


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python3 musicgen_wrapper.py "prompt" [duration_in_seconds]', file=sys.stderr)
        return 2

    prompt = sys.argv[1]
    duration = sys.argv[2] if len(sys.argv) > 2 else "30"
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(SCENE_SCRIPT),
        "--prompt",
        prompt,
        "--duration",
        duration,
        "--output",
        str(DEFAULT_OUTPUT),
    ]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
