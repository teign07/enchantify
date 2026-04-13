#!/usr/bin/env python3
"""
clear-lock.py — Remove the Enchantify session lock. Record session end time.
Pair to set-lock.py. Call at session close or on clean startup.
Usage: python3 scripts/clear-lock.py [player_name]
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

LOCK_PATH = Path('config/session-active.lock')

# Write session end state for the named player (used by session-entry.py)
player_name = sys.argv[1] if len(sys.argv) > 1 else None
if player_name:
    state_path = Path(f'players/{player_name}-session.json')
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except Exception:
            pass
    state['last_end'] = datetime.now().isoformat()
    state['session_count'] = state.get('session_count', 0) + 1
    state_path.write_text(json.dumps(state, indent=2))
    print(f"✓ Session state written → {state_path}")

if LOCK_PATH.exists():
    LOCK_PATH.unlink()
    print("✓ Session lock cleared.")
else:
    print("✓ No lock present (already clear).")
