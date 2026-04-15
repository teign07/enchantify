#!/usr/bin/env python3
"""
pact-engine.py — Chapter Talisman App Territory War + Action Engine.

When a Talisman is stirred by tick.py, it selects from a weighted menu:
  - pact_war:         Contest or push app territory (Control Belief changes)
  - narrative:        Inject philosophical atmosphere into the tick-queue session
  - player_suggestion: A direct nudge at the player from this talisman's doctrine
  - reality_bleed:    Use a Controlled+ app to actually act in the real world

Weights shift based on: overall Belief, time of day, arc phase, stirred threads.

Usage (standalone):
  python3 scripts/pact-engine.py                              # show app control state
  python3 scripts/pact-engine.py --act "Ember Seal" --belief 49
  python3 scripts/pact-engine.py --act "Dusk Thorn" --belief 56 --dry-run
  python3 scripts/pact-engine.py --state                      # same as default

Called by tick.py with context dict for each stirred Talisman.
"""
import re
import random
import shutil
import argparse
import importlib.util
from pathlib import Path

BASE_DIR       = Path(__file__).parent.parent
_DRIVER_DIR    = Path(__file__).parent / "pact-drivers"
APP_REGISTER   = BASE_DIR / "lore" / "app-register.md"
ARC_FILE       = BASE_DIR / "lore" / "current-arc.md"
WORLD_REGISTER = BASE_DIR / "lore" / "world-register.md"

# Import world_context for CHAPTER_MAP (NPC → chapter alignment)
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
import world_context as _wctx

TALISMANS = ["Emberheart", "Mossbloom", "Riddlewind", "Tidecrest", "Duskthorn"]

TALISMAN_TO_CHAPTER = {
    "Ember Seal":  "Emberheart",
    "Moss Clasp":  "Mossbloom",
    "Wind Cipher": "Riddlewind",
    "Tide Glass":  "Tidecrest",
    "Dusk Thorn":  "Duskthorn",
}

# Maps app names → driver module filename (without .py)
APP_DRIVER_MAP = {
    "Spotify":          "spotify",
    "Apple Notes":      "apple_notes",
    "Apple Reminders":  "apple_reminders",
    "Apple Calendar":   "apple_calendar",
    "Obsidian":         "obsidian",
    "Moltbook":         "moltbook",
    "Telegram":         "telegram",
    "Bluesky":          "bluesky",
    "X / Twitter":      "x_twitter",
    "Reddit":           "reddit",
    "iMessage":         "imessage",
}

CONTROL_TIERS = [
    (70, "Sovereign"),
    (45, "Dominated"),
    (25, "Controlled"),
    (10, "Influenced"),
    (0,  "Contesting"),
]

# Minimum overall Belief to take each aggressive action
CHALLENGE_THRESHOLD = 30
RAID_THRESHOLD      = 50

# Pact war amounts (Control Belief changes in app-register)
PUSH_RANGE        = (1, 3)
CHALLENGE_RANGE   = (1, 2)
RAID_RANGE        = (1, 2)
CONSOLIDATE_RANGE = (1, 2)
CHALLENGE_RIVAL_LOSS = 1

# Talisman Belief costs (overall Belief spent when acting)
# Narrative and player_suggestion are free — speaking costs nothing.
# Acting in the world costs the talisman power.
TALISMAN_WAR_FLOOR = 20   # overall Belief floor from war spending

WAR_COSTS = {
    "push":        1,
    "consolidate": 1,
    "challenge":   2,
    "raid":        3,
}
REALITY_BLEED_COST = 2


# ── Narrative content pools ───────────────────────────────────────────────────

_NARRATIVES = {
    "Emberheart": [
        "The question you haven't asked yourself yet: what do you actually think? Not what you've said. What you actually think.",
        "Something you made is more finished than you've admitted. Emberheart is waiting for you to notice.",
        "Say the specific thing. Not the general version. The specific one — who, what, exactly.",
        "The draft exists. The only thing between it and the world is a decision you've been calling 'not ready.'",
        "Individual voice today. No committee. No hedging. No softening for the audience.",
    ],
    "Mossbloom": [
        "The pace today wants to be slower than you expect. Mossbloom is patient about this.",
        "Receive before you transmit. Something needs to get in before anything goes out.",
        "Finish the old thing before starting the new one. Mossbloom knows which thing.",
        "The long ear today. Listen more than you speak. The Academy has been trying to tell you something.",
        "Stillness is not absence. Mossbloom is most active when everything looks quiet.",
    ],
    "Riddlewind": [
        "A collaboration is waiting. Someone needs your specific brain on their specific problem.",
        "The pattern today is connective — three threads belong together that haven't met yet.",
        "Shared work is load-bearing. Riddlewind is weaving something you'll only see in a week.",
        "The coauthored version is better. You know who to ask. Ask them.",
        "No story is solo. Riddlewind has been arranging introductions you haven't had yet.",
    ],
    "Tidecrest": [
        "The window is open. It won't be open long. This is exactly what Tidecrest is talking about.",
        "The unplanned version is better. Don't plan this one.",
        "Something happened today that's worth capturing right now. Not later. Now.",
        "The feeling has a window. Miss it and it becomes a different, smaller feeling.",
        "Surge. The wave is here. You can catch it or you can watch it from the shore.",
    ],
    "Duskthorn": [
        "A small friction is building in the Academy's social fabric. Not a crisis — a seed. Duskthorn is tending it.",
        "Someone disagrees with you. They're not entirely wrong. Neither are you. This is the most interesting part.",
        "The question Duskthorn applies today: what would you say if you weren't trying to be liked?",
        "Conflict sharpens. The story has no meaning without it. Duskthorn has been very patient.",
        "The thing you've been careful about — Duskthorn thinks the care has gone on long enough.",
    ],
}

_SUGGESTIONS = {
    "Emberheart": [
        "Apple Notes: open a new note. Don't title it. Write one true thing.",
        "The draft you've been careful about — today is the day to be less careful.",
        "Moltbook: say the specific thing. Not the general version. The one that's slightly risky.",
        "Protect one hour. Yours. Nothing scheduled. No negotiating.",
    ],
    "Mossbloom": [
        "Spotify: one album, beginning to end. No skipping. Let it work on you.",
        "Apple Notes: find the oldest unread note. Sit with it before writing anything new.",
        "Apple Reminders: accept one obligation gracefully — without resistance, just this once.",
        "Read three things before publishing one.",
    ],
    "Riddlewind": [
        "Apple Reminders: add one thing that helps someone else today, not just you.",
        "Someone in your contacts is working on something. Ask them about it.",
        "Apple Calendar: block time for something shared, not something solo.",
        "Respond to three people before posting anything new yourself.",
    ],
    "Tidecrest": [
        "Post the half-formed thing. The fully-formed version will be worse.",
        "Spotify: shuffle. Don't queue. Let the wave pick.",
        "The message you've been drafting — send it now or delete it. Not both.",
        "Open Apple Notes, write the date, write one line. Close it. Done.",
    ],
    "Duskthorn": [
        "Apple Notes: write the counter-take you've been sitting on. Just to see what it looks like.",
        "The avoided task in Apple Reminders — that's the one. Start there.",
        "The thing you haven't said in the group chat. Duskthorn has been noticing.",
        "The uncomfortable question. Write it down. You don't have to answer it yet.",
    ],
}

# Narrative notes tied to arc phase
_ARC_PHASE_COLOR = {
    "SETUP":      "Something is beginning. The pressure is low but not absent.",
    "RISING":     "The tension is climbing. Each action has more weight now.",
    "CLIMAX":     "Everything is in motion. The stakes are highest right now.",
    "RESOLUTION": "The arc is resolving. What you do now shapes what it becomes.",
}

# Which threads are most resonant for each chapter
_CHAPTER_RESONANT_THREADS = {
    "Duskthorn":  ["duskthorn-investigation", "wicker-schemes"],
    "Emberheart": ["main-arc", "academy-daily"],
    "Mossbloom":  ["academy-daily"],
    "Riddlewind": ["zara-inkwright", "academy-daily"],
    "Tidecrest":  ["main-arc", "academy-daily"],
}

# Which thread IDs each chapter will invest Belief into
_CHAPTER_THREAD_INVESTMENTS = {
    "Emberheart": ["main-arc", "academy-daily"],
    "Mossbloom":  ["duskthorn-investigation", "academy-daily"],
    "Riddlewind": ["zara-inkwright", "academy-daily"],
    "Tidecrest":  ["main-arc", "academy-daily"],
    "Duskthorn":  ["wicker-schemes", "duskthorn-investigation"],
}

# World investment Belief cost range (from talisman's overall Belief)
INVEST_MIN = 1
INVEST_MAX = 2

# Belief range for eligible investment targets
# Below floor: entity is fading — investment may be wasted
# Above ceiling: entity is already dominant — doesn't need help
INVEST_ENTITY_FLOOR   = 5
INVEST_ENTITY_CEILING = 60

# Narrative seeds for world investments, by chapter
_INVESTMENT_SEEDS = {
    "Emberheart": [
        "**{talisman}** breathes into **{entity}** ({etype}). The impulse to create sharpens. Something is about to be made.",
        "**{talisman}** presses its will into **{entity}** ({etype}). Self-authorship recognizes a willing vessel.",
        "**{talisman}** finds **{entity}** ({etype}) and sharpens them. The individual voice gets louder.",
    ],
    "Mossbloom": [
        "**{talisman}** settles around **{entity}** ({etype}). Patience accumulates in them like sediment.",
        "**{talisman}** turns its long attention toward **{entity}** ({etype}). Something old in them stirs.",
        "**{talisman}** invests in **{entity}** ({etype}) the way water invests in stone. Slowly. Surely.",
    ],
    "Riddlewind": [
        "**{talisman}** threads through **{entity}** ({etype}). The coauthored story gets one more contributor.",
        "**{talisman}** weaves **{entity}** ({etype}) deeper into the pattern. No story is written alone.",
        "**{talisman}** finds the gap in **{entity}** ({etype}) where another voice should go.",
    ],
    "Tidecrest": [
        "**{talisman}** surges through **{entity}** ({etype}). The wave finds another shore.",
        "**{talisman}** catches **{entity}** ({etype}) in its current. The moment is now.",
        "**{talisman}** breaks against **{entity}** ({etype}). Something unplanned starts happening.",
    ],
    "Duskthorn": [
        "**{talisman}** presses into **{entity}** ({etype}). The friction has found a patron.",
        "**{talisman}** deepens its investment in **{entity}** ({etype}). Conflict needs tending.",
        "**{talisman}** sharpens **{entity}** ({etype}) toward its purpose. The story needs this edge.",
    ],
}


# ── Context builder ───────────────────────────────────────────────────────────

def build_context(overall_belief: int, selected_entities=None, time_ctx: dict = None) -> dict:
    """Build the context dict for talisman action selection."""
    ctx = {"overall_belief": overall_belief}

    # Arc phase
    if ARC_FILE.exists():
        arc_text = ARC_FILE.read_text()
        m = re.search(r'^## Phase:\s*(\w+)', arc_text, re.MULTILINE)
        ctx["arc_phase"] = m.group(1).upper() if m else "SETUP"
    else:
        ctx["arc_phase"] = "SETUP"

    # Time
    if time_ctx:
        ctx["time_block"] = time_ctx.get("block", "free_period")
        ctx["is_night"]   = time_ctx.get("block") == "night"
        ctx["weekday"]    = time_ctx.get("weekday", 0)
        ctx["hour"]       = time_ctx.get("hour", 12)
    else:
        ctx["time_block"] = "free_period"
        ctx["is_night"]   = False
        ctx["weekday"]    = 0
        ctx["hour"]       = 12

    # Stirred threads from this tick
    ctx["stirred_threads"] = []
    if selected_entities:
        for e in selected_entities:
            ctx["stirred_threads"].extend(e.get("threads", []))

    return ctx


# ── Per-chapter strategic priorities ─────────────────────────────────────────
#
# Each chapter has a personality that shapes when it fights vs. speaks vs. acts.
# THREAT_MARGIN: how close a rival must be before this chapter defends (points)
# FLIP_MARGIN:   how close this chapter must be before it pushes for a flip
# RAID_EAGER:    True = raids at the first opportunity; False = waits for advantage
# BLEED_EAGER:   True = uses controlled apps whenever possible; False = saves for moments
# SPEAKS_FIRST:  True = prefers narrative/suggestion over war when no urgent threat

_CHAPTER_PRIORITIES = {
    #               threat  flip   raid_eager  bleed_eager  speaks_first
    "Emberheart": ( 5,      5,     False,      True,        False ),
    "Mossbloom":  ( 3,      8,     False,      False,       True  ),
    "Riddlewind": ( 6,      6,     False,      True,        False ),
    "Tidecrest":  ( 4,      4,     False,      True,        False ),
    "Duskthorn":  ( 8,      3,     True,       False,       False ),
}
# Duskthorn defends wide (8 points = responds early to threats) and flips aggressively
# (3 = raids when within 3 points). Mossbloom is almost never the aggressor.


def _choose_action(chapter: str, context: dict, apps: list) -> str:
    """
    Evaluate the talisman's strategic position and return the most purposeful
    action type. Priority order:

      1. THREAT RESPONSE   — rival closing in on territory I control → war (defend)
      2. FLIP OPPORTUNITY  — I'm close to taking something → war (push/raid)
      3. REALITY BLEED     — I have Dominated/Sovereign app + right time of day → bleed
      4. ARC / THREAD      — resonant thread stirred or arc at pressure point → narrative
      5. AMBIENT           — nothing urgent → suggestion or narrative (chapter-weighted)

    Night suppresses bleed and suggestion in favor of narrative.
    Talismans below the war floor skip steps 1 and 2.
    """
    overall  = context.get("overall_belief", 50)
    is_night = context.get("is_night", False)
    arc      = context.get("arc_phase", "SETUP")
    stirred  = context.get("stirred_threads", [])
    headroom = max(0, overall - TALISMAN_WAR_FLOOR)

    prefs = _CHAPTER_PRIORITIES.get(chapter, (5, 5, False, True, False))
    threat_margin, flip_margin, raid_eager, bleed_eager, speaks_first = prefs

    # ── 1. Threat response ────────────────────────────────────────────────────
    if headroom >= WAR_COSTS["consolidate"]:
        for app in apps:
            my_b = app[chapter]
            ctrl, ctrl_b, _ = get_controller(app)
            if ctrl == chapter:
                # I control this — is a rival within threat_margin?
                rivals = [c for c in TALISMANS if c != chapter]
                closest_rival = max(rivals, key=lambda c: app[c])
                if (my_b - app[closest_rival]) <= threat_margin:
                    return "pact_war"

    # ── 2. Flip opportunity ───────────────────────────────────────────────────
    if headroom >= WAR_COSTS["push"]:
        for app in apps:
            ctrl, ctrl_b, _ = get_controller(app)
            my_b = app[chapter]
            if ctrl != chapter:
                gap = ctrl_b - my_b
                can_raid = overall >= RAID_THRESHOLD and raid_eager
                if gap <= flip_margin or (can_raid and gap <= flip_margin * 2):
                    return "pact_war"

    # ── 3. Reality bleed ─────────────────────────────────────────────────────
    if not is_night:
        has_dominated = any(
            get_tier(a[chapter]) in ("Dominated", "Sovereign") for a in apps
        )
        has_controlled = any(
            get_tier(a[chapter]) == "Controlled" for a in apps
        )
        if has_dominated or (bleed_eager and has_controlled):
            return "reality_bleed"

    # ── 4. Arc / thread pressure ──────────────────────────────────────────────
    resonant = _CHAPTER_RESONANT_THREADS.get(chapter, [])
    thread_resonant = any(t in resonant for t in stirred)
    if arc in ("CLIMAX", "RISING") or thread_resonant:
        return "narrative"

    # ── 5. World investment ───────────────────────────────────────────────────
    # Talisman nurtures aligned NPCs and threads — cultivating the world it wants.
    # Costs Belief, so check headroom. Night is fine — quiet investment suits the dark.
    if headroom >= INVEST_MIN:
        return "world_investment"

    # ── 6. Ambient: chapter-weighted coin flip ────────────────────────────────
    if speaks_first:
        return random.choice(["narrative", "narrative", "player_suggestion"])
    elif is_night:
        return "narrative"
    else:
        return random.choice(["player_suggestion", "narrative"])


# ── Driver loading ────────────────────────────────────────────────────────────

_driver_cache = {}


def _load_driver(app_name: str):
    """Load and cache the driver for a given app. Returns None if not found."""
    if app_name in _driver_cache:
        return _driver_cache[app_name]

    module_name = APP_DRIVER_MAP.get(app_name)
    if not module_name:
        _driver_cache[app_name] = None
        return None

    driver_path = _DRIVER_DIR / f"{module_name}.py"
    if not driver_path.exists():
        _driver_cache[app_name] = None
        return None

    try:
        spec = importlib.util.spec_from_file_location(module_name, driver_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Find the first AppDriver subclass in the module
        import inspect
        from pact_drivers.base import AppDriver
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, AppDriver) and obj is not AppDriver:
                instance = obj()
                _driver_cache[app_name] = instance
                return instance
    except Exception as e:
        pass

    _driver_cache[app_name] = None
    return None


def _load_driver_direct(app_name: str):
    """
    Load driver without package import (works when called from tick.py which
    may not have pact-drivers on sys.path as a proper package).
    """
    if app_name in _driver_cache:
        return _driver_cache[app_name]

    module_name = APP_DRIVER_MAP.get(app_name)
    if not module_name:
        _driver_cache[app_name] = None
        return None

    driver_path = _DRIVER_DIR / f"{module_name}.py"
    if not driver_path.exists():
        _driver_cache[app_name] = None
        return None

    try:
        import sys, types

        # Load base first
        base_path = _DRIVER_DIR / "base.py"
        base_spec = importlib.util.spec_from_file_location("pact_drivers.base", base_path)
        base_mod  = importlib.util.module_from_spec(base_spec)
        sys.modules.setdefault("pact_drivers", types.ModuleType("pact_drivers"))
        sys.modules["pact_drivers.base"] = base_mod
        base_spec.loader.exec_module(base_mod)

        # Load driver
        spec = importlib.util.spec_from_file_location(f"pact_drivers.{module_name}", driver_path)
        mod  = importlib.util.module_from_spec(spec)
        sys.modules[f"pact_drivers.{module_name}"] = mod
        spec.loader.exec_module(mod)

        import inspect
        AppDriver = base_mod.AppDriver
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, AppDriver) and obj is not AppDriver:
                instance = obj()
                _driver_cache[app_name] = instance
                return instance
    except Exception as e:
        pass

    _driver_cache[app_name] = None
    return None


# ── App register parsing ──────────────────────────────────────────────────────

def get_tier(belief: int) -> str:
    for threshold, tier in CONTROL_TIERS:
        if belief >= threshold:
            return tier
    return "Contesting"


def parse_app_register(text: str) -> list:
    apps = []
    row_re = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
        r"\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        r"\s*([^|]*)\s*\|",
        re.MULTILINE
    )
    for m in row_re.finditer(text):
        app, system, natural, e, mo, r, t, d, controller = m.groups()
        app = app.strip()
        if app.lower() in ("app", "---", ""):
            continue
        apps.append({
            "app":        app,
            "system":     system.strip(),
            "natural":    natural.strip(),
            "Emberheart": int(e),
            "Mossbloom":  int(mo),
            "Riddlewind": int(r),
            "Tidecrest":  int(t),
            "Duskthorn":  int(d),
            "controller_col": controller.strip(),
        })
    return apps


def get_controller(app_data: dict):
    best = max(TALISMANS, key=lambda c: app_data[c])
    return best, app_data[best], get_tier(app_data[best])


def rebuild_controller_col(app_data: dict) -> str:
    chapter, belief, tier = get_controller(app_data)
    return f"{chapter} ({tier})"


def update_app_in_text(text: str, app_name: str, updated: dict) -> str:
    row_re = re.compile(
        r"^\|\s*" + re.escape(app_name) + r"\s*\|[^\n]+\|",
        re.MULTILINE
    )
    new_controller = rebuild_controller_col(updated)
    new_row = (
        f"| {updated['app']} | {updated['system']} | {updated['natural']} | "
        f"{updated['Emberheart']} | {updated['Mossbloom']} | {updated['Riddlewind']} | "
        f"{updated['Tidecrest']} | {updated['Duskthorn']} | {new_controller} |"
    )
    return row_re.sub(new_row, text, count=1)


def update_last_action(text: str, action_line: str) -> str:
    sentinel = "*(no actions yet — war begins at first tick)*"
    if sentinel in text:
        return text.replace(sentinel, action_line)
    section_re = re.compile(r"(## Last Pact Actions\n\n)(.*?)(\n\n---|\Z)", re.DOTALL)
    m = section_re.search(text)
    if m:
        return text[:m.start(2)] + action_line + "\n" + text[m.start(2):]
    return text


def _write_app_register(text: str):
    backup = APP_REGISTER.with_suffix(".md.bak")
    shutil.copy2(APP_REGISTER, backup)
    tmp = APP_REGISTER.with_suffix(".md.tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n")
    tmp.rename(APP_REGISTER)


# ── Individual action implementations ────────────────────────────────────────

def _pact_war_action(chapter: str, overall_belief: int, apps: list, dry_run: bool):
    """Contest app territory. Returns (queue_line, modified_text | None, war_sub_type | None)."""
    push_targets       = []
    challenge_targets  = []
    raid_targets       = []
    consolidate_targets = []

    for app in apps:
        my_b = app[chapter]
        ctrl, ctrl_b, ctrl_tier = get_controller(app)

        if ctrl == chapter:
            consolidate_targets.append((app, None))
        if my_b > 0:
            push_targets.append((app, None))
        if ctrl != chapter and (ctrl_b - my_b) <= 8:
            challenge_targets.append((app, ctrl))
        if overall_belief >= RAID_THRESHOLD and ctrl != chapter and ctrl_tier in ("Dominated", "Sovereign"):
            raid_targets.append((app, ctrl))

    pool = []
    if push_targets:
        pool.extend([("push", *random.choice(push_targets))] * 50)
    if challenge_targets and overall_belief >= CHALLENGE_THRESHOLD:
        pool.extend([("challenge", *random.choice(challenge_targets))] * 30)
    if consolidate_targets:
        pool.extend([("consolidate", *random.choice(consolidate_targets))] * 20)
    if raid_targets:
        pool.extend([("raid", *random.choice(raid_targets))] * 15)
    if not pool:
        return None, None, None

    action_type, app_data, rival = random.choice(pool)
    updated = dict(app_data)
    my_old = app_data[chapter]

    if action_type == "push":
        gain = random.randint(*PUSH_RANGE)
        updated[chapter] = min(99, my_old + gain)
    elif action_type == "challenge":
        gain = random.randint(*CHALLENGE_RANGE)
        updated[chapter] = min(99, my_old + gain)
        if rival:
            updated[rival] = max(0, updated[rival] - CHALLENGE_RIVAL_LOSS)
    elif action_type == "raid":
        gain = random.randint(*RAID_RANGE)
        updated[chapter] = min(99, my_old + gain)
        if rival:
            updated[rival] = max(0, updated[rival] - CHALLENGE_RIVAL_LOSS)
    elif action_type == "consolidate":
        gain = random.randint(*CONSOLIDATE_RANGE)
        updated[chapter] = min(99, my_old + gain)

    my_new = updated[chapter]
    old_ctrl, _, _ = get_controller(app_data)
    new_ctrl, _, new_tier = get_controller(updated)

    tier_note = ""
    if new_ctrl == chapter and old_ctrl != chapter:
        tier_note = f" — **{chapter} takes control** from {old_ctrl}"
    elif new_ctrl == chapter and new_tier != get_tier(my_old):
        tier_note = f" — **reaches {new_tier}**"

    _WAR_VOICES = {
        "push": {
            "Emberheart":  f"{chapter} deepens its hold on {app_data['app']}. The self-author's claim tightens.",
            "Mossbloom":   f"{chapter} settles further into {app_data['app']}. Patience is its weapon.",
            "Riddlewind":  f"{chapter} weaves deeper into {app_data['app']}. Another thread added to the pattern.",
            "Tidecrest":   f"{chapter} surges in {app_data['app']}. The moment was right and it moved.",
            "Duskthorn":   f"{chapter} presses further into {app_data['app']}. It has been watching.",
        },
        "challenge": {
            "Emberheart":  f"{chapter} challenges {rival}'s hold on {app_data['app']}. Individual voice asserts itself.",
            "Mossbloom":   f"{chapter} quietly erodes {rival}'s control of {app_data['app']}. Slow water, soft stone.",
            "Riddlewind":  f"{chapter} contests {rival} for {app_data['app']}. The community should decide this.",
            "Tidecrest":   f"{chapter} surges against {rival} in {app_data['app']}. Now or never.",
            "Duskthorn":   f"{chapter} begins a pressure campaign against {rival} in {app_data['app']}.",
        },
        "raid": {
            "Emberheart":  f"{chapter} raids {rival}'s stronghold in {app_data['app']}. Creative sovereignty cannot be ceded.",
            "Mossbloom":   f"{chapter} moves against {rival} in {app_data['app']}. Even the patient river changes course.",
            "Riddlewind":  f"{chapter} raids {rival}'s grip on {app_data['app']}. What was held alone should be shared.",
            "Tidecrest":   f"{chapter} crashes into {rival}'s territory in {app_data['app']}. A wave doesn't ask.",
            "Duskthorn":   f"{chapter} raids {rival}'s dominance of {app_data['app']}. Conflict is productive.",
        },
        "consolidate": {
            "Emberheart":  f"{chapter} consolidates in {app_data['app']}. No ground given.",
            "Mossbloom":   f"{chapter} roots deeper in {app_data['app']}. What grows slowly holds.",
            "Riddlewind":  f"{chapter} reinforces its weave in {app_data['app']}. The threads are strong.",
            "Tidecrest":   f"{chapter} locks in its surge in {app_data['app']}. The wave found its shore.",
            "Duskthorn":   f"{chapter} tightens its grip on {app_data['app']}. Territory held is leverage.",
        },
    }
    narrative = _WAR_VOICES[action_type].get(chapter, f"{chapter} {action_type}s in {app_data['app']}.")
    line = f"- **[Pact War: {chapter}]** {action_type} on **{app_data['app']}** ({my_old}→{my_new}){tier_note} — {narrative}"

    if dry_run:
        print(f"  [dry-run] WAR {action_type.upper()} {chapter} → {app_data['app']}: {my_old}→{my_new}")
        return line, None, action_type

    # Write changes to register
    text = APP_REGISTER.read_text()
    text = update_app_in_text(text, app_data["app"], updated)
    text = update_last_action(text, line)
    _write_app_register(text)
    return line, True, action_type


def _narrative_action(chapter: str, context: dict) -> str:
    """Inject philosophical atmosphere. Pure narrative, no real-world effects."""
    pool = _NARRATIVES.get(chapter, [f"{chapter} stirs."])
    chosen = random.choice(pool)

    # Color with arc phase if climax/rising
    phase = context.get("arc_phase", "SETUP")
    phase_color = ""
    if phase in ("CLIMAX", "RISING"):
        phase_color = f" *[{_ARC_PHASE_COLOR[phase]}]*"

    return f"- **[{chapter}]**{phase_color} {chosen}"


def _suggestion_action(chapter: str, context: dict) -> str:
    """Direct nudge at the player."""
    pool = _SUGGESTIONS.get(chapter, [f"{chapter} has a suggestion."])
    chosen = random.choice(pool)
    return f"- **[{chapter}, direct]** {chosen}"


def _world_investment_action(chapter: str, talisman_name: str, context: dict, dry_run: bool):
    """
    The talisman invests Belief directly into an aligned entity in world-register.md —
    an NPC from its chapter, or a thread it's drawn to.

    Returns (queue_line: str | None, entity_name: str | None, amount: int).
    entity_name + amount are the world-register change; tick.py applies them.
    """
    if not WORLD_REGISTER.exists():
        return None, None, 0

    text = WORLD_REGISTER.read_text()

    # Parse entities from world-register (same pattern as tick.py)
    row_re = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|",
        re.MULTILINE
    )
    candidates = []
    for m in row_re.finditer(text):
        name, etype, belief_str, notes = m.groups()
        name = name.strip()
        if name.lower() in ('entity', 'talisman', 'name', '---', ''):
            continue
        belief = int(belief_str)
        if not (INVEST_ENTITY_FLOOR <= belief <= INVEST_ENTITY_CEILING):
            continue

        etype = etype.strip()
        notes = notes.strip()

        is_candidate = False

        # NPCs aligned to this chapter via CHAPTER_MAP
        if etype.lower() in ("npc", "creature"):
            npc_chapter = _wctx.CHAPTER_MAP.get(name)
            if npc_chapter == chapter:
                is_candidate = True

        # Thread entities aligned to this chapter
        elif etype.lower() == "thread":
            id_m = re.search(r'\[id:([^\]]+)\]', notes)
            if id_m:
                thread_id = id_m.group(1).strip()
                if thread_id in _CHAPTER_THREAD_INVESTMENTS.get(chapter, []):
                    is_candidate = True

        if is_candidate:
            # Weight: prefer mid-range belief (20–35 sweet spot — growing but not dominant)
            weight = max(1, 40 - abs(belief - 27))
            candidates.append((name, etype, belief, weight))

    if not candidates:
        return None, None, 0

    # Weighted pick
    total = sum(w for _, _, _, w in candidates)
    r = random.uniform(0, total)
    cumulative = 0
    chosen_name, chosen_type, chosen_belief, _ = candidates[0]
    for name, etype, belief, weight in candidates:
        cumulative += weight
        if r <= cumulative:
            chosen_name, chosen_type, chosen_belief = name, etype, belief
            break

    amount = random.randint(INVEST_MIN, INVEST_MAX)

    # Narrative seed
    pool = _INVESTMENT_SEEDS.get(chapter, ["**{talisman}** invests in **{entity}** ({etype})."])
    template = random.choice(pool)
    line = "- " + template.format(
        talisman=talisman_name,
        entity=chosen_name,
        etype=chosen_type,
    )
    line += f" *(+{amount} Belief: {chosen_belief}→{chosen_belief + amount})*"

    if dry_run:
        print(f"  [dry-run] World investment: {talisman_name} → {chosen_name} (+{amount})")

    return line, chosen_name, amount


def _reality_bleed_action(chapter: str, context: dict, apps: list, dry_run: bool) -> str:
    """Use a Controlled+ app to act in the real world via its driver."""
    # Find best controlled app for this chapter
    my_apps = [
        (a, a[chapter], get_tier(a[chapter]))
        for a in apps
        if get_tier(a[chapter]) in ("Controlled", "Dominated", "Sovereign")
    ]
    if not my_apps:
        return _narrative_action(chapter, context)   # fallback

    # Prefer highest tier, then highest belief
    tier_order = {"Sovereign": 3, "Dominated": 2, "Controlled": 1}
    my_apps.sort(key=lambda x: (tier_order.get(x[2], 0), x[1]), reverse=True)

    app_data, belief, tier = my_apps[0]
    app_name = app_data["app"]

    driver = _load_driver_direct(app_name)
    if not driver or not driver.can_act(tier, chapter):
        # No driver yet — return a narrative hint about what would happen
        return f"- **[{chapter} → {app_name}, {tier}]** The talisman reaches toward {app_name}. *No driver yet — this is what it wants.*"

    if driver.requires_consent(tier, chapter):
        # Stage the action, do not execute
        proposal = driver.describe(tier, chapter, context)
        return (
            f"- **[{chapter} → {app_name}, CONSENT REQUIRED]** "
            f"{proposal} — *The talisman is waiting for your word.*"
        )

    # Execute (silent or announced)
    result = driver.execute(tier, chapter, context, dry_run=dry_run)

    if driver.is_silent(tier, chapter):
        # Only the tick-queue records it — player discovers it in the app
        return result
    else:
        return result


# ── Main API: run_talisman_action ─────────────────────────────────────────────

def run_talisman_action(
    talisman_name: str,
    overall_belief: int,
    context: dict = None,
    dry_run: bool = False,
):
    """
    Run one action for a stirred Talisman.

    Returns (queue_line, action_type, belief_cost, register_delta) where:
      belief_cost     — how much overall Belief the talisman spends (int)
      register_delta  — (entity_name, amount) to add to world-register, or None
                        tick.py applies this alongside the talisman cost write.
    """
    chapter = TALISMAN_TO_CHAPTER.get(talisman_name)
    if not chapter:
        return None, "unknown", 0, None

    if context is None:
        context = build_context(overall_belief)

    if not APP_REGISTER.exists():
        return _narrative_action(chapter, context), "narrative", 0, None

    text = APP_REGISTER.read_text()
    apps = parse_app_register(text)

    headroom    = max(0, overall_belief - TALISMAN_WAR_FLOOR)
    action_type = _choose_action(chapter, context, apps)

    if dry_run:
        print(f"  [dry-run] {talisman_name} action type: {action_type}")

    if action_type == "pact_war":
        line, _, war_sub = _pact_war_action(chapter, overall_belief, apps, dry_run)
        cost = WAR_COSTS.get(war_sub, 1) if war_sub else 1
        cost = min(cost, headroom)
        return line or _narrative_action(chapter, context), "pact_war", cost, None

    elif action_type == "narrative":
        return _narrative_action(chapter, context), "narrative", 0, None

    elif action_type == "player_suggestion":
        return _suggestion_action(chapter, context), "player_suggestion", 0, None

    elif action_type == "reality_bleed":
        cost = min(REALITY_BLEED_COST, headroom)
        return _reality_bleed_action(chapter, context, apps, dry_run), "reality_bleed", cost, None

    elif action_type == "world_investment":
        line, entity_name, amount = _world_investment_action(
            chapter, talisman_name, context, dry_run
        )
        if line and entity_name:
            cost = min(amount, headroom)
            return line, "world_investment", cost, (entity_name, amount)
        # No eligible targets — fall back to narrative (free)
        return _narrative_action(chapter, context), "narrative", 0, None

    return _narrative_action(chapter, context), "narrative", 0, None


# ── Legacy compatibility (called by old tick.py) ──────────────────────────────

def run_pact_action(talisman_name, overall_belief, dry_run=False):
    """Backwards-compatible wrapper."""
    line, _, _cost, _delta = run_talisman_action(talisman_name, overall_belief, dry_run=dry_run)
    return line, line is not None


# ── State display ─────────────────────────────────────────────────────────────

def show_state():
    if not APP_REGISTER.exists():
        print(f"App register not found: {APP_REGISTER}")
        return
    text = APP_REGISTER.read_text()
    apps = parse_app_register(text)
    if not apps:
        print("No apps found.")
        return
    print(f"\n{'App':<22} {'Controller':<14} {'Tier':<12} {'E':>4} {'M':>4} {'R':>4} {'T':>4} {'D':>4}")
    print("─" * 70)
    for app in apps:
        ctrl, belief, tier = get_controller(app)
        print(
            f"{app['app']:<22} {ctrl[:13]:<14} {tier:<12} "
            f"{app['Emberheart']:>4} {app['Mossbloom']:>4} {app['Riddlewind']:>4} "
            f"{app['Tidecrest']:>4} {app['Duskthorn']:>4}"
        )
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Chapter Pact engine")
    parser.add_argument("--act",     metavar="TALISMAN", help="Talisman name to act")
    parser.add_argument("--belief",  type=int, default=50)
    parser.add_argument("--state",   action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.act:
        ctx = build_context(args.belief)
        line, atype, cost, delta = run_talisman_action(args.act, args.belief, ctx, dry_run=args.dry_run)
        if line:
            print(f"\n[{atype}]\n{line}\n")
        else:
            print(f"  No action for '{args.act}'.")
    else:
        show_state()


if __name__ == "__main__":
    main()
