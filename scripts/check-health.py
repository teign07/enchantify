#!/usr/bin/env python3
"""Diagnose Enchantify's Health Auto Export heartbeat input."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
PULSE = BASE / "scripts" / "pulse.py"


def load_pulse():
    spec = importlib.util.spec_from_file_location("pulse", PULSE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    pulse = load_pulse()
    health_dir_cfg = pulse._cfg_get("HEALTH_DIR", "")
    health_dir = Path(health_dir_cfg).expanduser() if health_dir_cfg else Path(
        "~/Library/Mobile Documents/iCloud~com~ifunography~HealthExport/Documents"
    ).expanduser()

    print(f"HEALTH_BACKEND: {pulse._cfg_get('HEALTH_BACKEND', 'health_auto_export')}")
    print(f"HEALTH_DIR: {health_dir}")
    print(f"HEALTH_DIR_EXISTS: {health_dir.exists()}")

    try:
        candidate_dirs = pulse._health_candidate_dirs(str(health_dir))
        print(f"CANDIDATE_DIRS: {len(candidate_dirs)}")
        for item in candidate_dirs[:6]:
            print(f"- {item}")
    except Exception as e:
        print(f"CANDIDATE_DIRS_ERROR: {type(e).__name__}: {e}")

    result = pulse.get_health()
    print(f"RESULT: {result}")

    cache_path = Path(pulse.HEALTH_CACHE)
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
            print(f"CACHE_UPDATED_AT: {cache.get('updated_at')}")
            print(f"CACHE_SOURCE: {cache.get('source_path')}")
        except Exception as e:
            print(f"CACHE_ERROR: {e}")
    else:
        print("CACHE: missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
