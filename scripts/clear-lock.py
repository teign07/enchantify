#!/usr/bin/env python3
"""
clear-lock.py — Remove the Enchantify session lock.
Pair to set-lock.py. Call at session close or on clean startup.
Usage: python3 scripts/clear-lock.py
"""
import os

LOCK_PATH = 'config/session-active.lock'

if os.path.exists(LOCK_PATH):
    os.remove(LOCK_PATH)
    print("✓ Session lock cleared.")
else:
    print("✓ No lock present (already clear).")
