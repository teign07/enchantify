#!/usr/bin/env python3
"""Shared Belief caps for Enchantify systems.

This keeps world-register writers from disagreeing about ceilings.
"""

from __future__ import annotations

import re

PLAYER_CAP = 100
NPC_CAP = 100
ENTITY_CAP = 100
THREAD_CAP = 65
TALISMAN_CAP = 200
MIN_BELIEF = 0

TALISMAN_NAMES = {
    "tide glass",
    "wind cipher",
    "ember seal",
    "moss clasp",
    "dusk thorn",
}

CHAPTER_TYPES = {
    "tidecrest",
    "riddlewind",
    "emberheart",
    "mossbloom",
    "duskthorn",
}


def norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def is_talisman(name: str | None = None, entity_type: str | None = None, explicit: bool = False) -> bool:
    if explicit:
        return True
    return norm(name) in TALISMAN_NAMES or norm(entity_type) in CHAPTER_TYPES or norm(entity_type) == "talisman"


def cap_for(entity_type: str | None = None, name: str | None = None, *, explicit_talisman: bool = False) -> int:
    etype = norm(entity_type)
    if etype == "player":
        return PLAYER_CAP
    if etype == "thread":
        return THREAD_CAP
    if is_talisman(name, entity_type, explicit_talisman):
        return TALISMAN_CAP
    if etype in {"npc", "creature"}:
        return NPC_CAP
    return ENTITY_CAP


def clamp_belief(value: int, entity_type: str | None = None, name: str | None = None, *, explicit_talisman: bool = False) -> int:
    return max(MIN_BELIEF, min(cap_for(entity_type, name, explicit_talisman=explicit_talisman), int(value)))


def cap_label(entity_type: str | None = None, name: str | None = None, *, explicit_talisman: bool = False) -> str:
    return str(cap_for(entity_type, name, explicit_talisman=explicit_talisman))
