#!/usr/bin/env python3
"""
wallpaper.py — Living Academy wallpaper for the player's desktop.

The wallpaper is always bj's dorm room — same composition, changing details.
What varies: the light (belief), the window (real weather/time), the edges
(Nothing pressure), one subtle arc element, one NPC trace.

It's a painting that happens to know things. Never a dashboard.

Architecture
────────────
Python handles: state detection, prompt construction, OS integration, archiving.
The Labyrinth handles: image generation (it has the image_generate tool).

Workflow
────────
1. At session open: `python3 scripts/wallpaper.py --check [player]`
   → Outputs REGENERATE: YES or NO, and if YES, the full image prompt.
2. Labyrinth reads output. If YES: calls image_generate with the prompt,
   size="1792x1024". Then runs `python3 scripts/wallpaper.py --set [path]`.
3. `--set [path]` copies to wallpapers/, sets macOS desktop, saves state.

Background generation (no active session):
   `python3 scripts/wallpaper.py --generate [player]`
   → Calls openclaw agent, which calls image_generate. Best-effort.

Usage
─────
  python3 scripts/wallpaper.py --check [player]    # Should we regenerate?
  python3 scripts/wallpaper.py --set [path]        # Labyrinth calls this post-gen
  python3 scripts/wallpaper.py --generate [player] # Background gen via agent
  python3 scripts/wallpaper.py --force [player]    # Force regenerate regardless
  python3 scripts/wallpaper.py --prompt [player]   # Print prompt only, no gen
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE  = SCRIPT_DIR.parent

WALLPAPER_DIR   = WORKSPACE / "wallpapers"
STATE_FILE      = WALLPAPER_DIR / "state.json"
ARCHIVE_KEEP    = 10       # keep last N wallpapers
COOLDOWN_HOURS  = 2        # minimum hours between generations
STALE_HOURS     = 8        # regenerate even if state unchanged after this long


# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(sig: str, path: str, detail: dict) -> None:
    WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "last_generated":  datetime.now().isoformat(),
        "last_path":       path,
        "state_signature": sig,
        "detail":          detail,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))


def hours_since(iso_str: str) -> float:
    if not iso_str:
        return 9999.0
    try:
        then = datetime.fromisoformat(iso_str)
        return (datetime.now() - then).total_seconds() / 3600
    except Exception:
        return 9999.0


# ── Read game state ───────────────────────────────────────────────────────────

def read_safe(path: Path, limit: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text().strip()
    return "\n".join(text.splitlines()[:limit]) if limit else text


def get_belief(player_name: str) -> int:
    text = read_safe(WORKSPACE / "players" / f"{player_name}.md", 10)
    m = re.search(r"\*\*Belief:\*\*\s*(\d+)", text)
    return int(m.group(1)) if m else 50


def get_nothing_level() -> str:
    text = read_safe(WORKSPACE / "lore" / "nothing-intelligence.md", 20)
    m = re.search(r"Pressure level:\s*(\w+)", text, re.IGNORECASE)
    raw = m.group(1).lower() if m else "moderate"
    # Normalise to our 5-point scale
    if raw in ("healed", "none", "absent"):
        return "healed"
    elif raw in ("low", "minimal"):
        return "low"
    elif raw in ("moderate", "medium"):
        return "moderate"
    elif raw in ("high", "elevated"):
        return "high"
    elif raw in ("critical", "extreme", "attack"):
        return "critical"
    return "moderate"


def get_weather_and_time() -> dict:
    """Extract weather, hour, moon from HEARTBEAT.md pulse block."""
    hb = read_safe(WORKSPACE / "HEARTBEAT.md", 60)
    result = {"hour": datetime.now().hour, "weather": "Overcast", "moon": "Waning Crescent", "temp_f": 50}

    # Hour from pulse timestamp
    m = re.search(r"Pulse\s*[—–-]+\s*(\d{1,2}):(\d{2})\s*(AM|PM)", hb, re.IGNORECASE)
    if m:
        h = int(m.group(1))
        pm = m.group(3).upper() == "PM"
        if pm and h != 12:
            h += 12
        elif not pm and h == 12:
            h = 0
        result["hour"] = h

    # Weather
    m = re.search(r"Belfast Feel:\*\*\s*(.+)", hb)
    if m:
        result["weather"] = m.group(1).strip()[:80]

    # Raw weather line for temp
    m = re.search(r"Raw:.*?(\d+)°F", hb)
    if m:
        result["temp_f"] = int(m.group(1))

    # Moon
    m = re.search(r"Moon:\*\*\s*(.+)", hb)
    if m:
        result["moon"] = m.group(1).strip()[:60]

    return result


def get_arc_phase() -> str:
    text = read_safe(WORKSPACE / "lore" / "current-arc.md", 20)
    m = re.search(r"Phase:\s*(\w+)", text, re.IGNORECASE)
    return m.group(1).upper() if m else "SETUP"


def get_arc_premise() -> str:
    text = read_safe(WORKSPACE / "lore" / "current-arc.md", 30)
    m = re.search(r"Premise:\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip()[:120] if m else ""


def get_stirred_npc() -> str:
    """Most recently stirred NPC from tick-queue, for the NPC trace."""
    text = read_safe(WORKSPACE / "memory" / "tick-queue.md", 40)
    for npc in ["Zara", "Boggle", "Thorne", "Momort", "Euphony", "Villanelle", "Stonebrook", "Wicker"]:
        if npc.lower() in text.lower():
            return npc
    return ""


def get_game_detail(player_name: str) -> dict:
    belief      = get_belief(player_name)
    nothing     = get_nothing_level()
    wt          = get_weather_and_time()
    arc_phase   = get_arc_phase()
    arc_premise = get_arc_premise()
    npc         = get_stirred_npc()

    # Belief bracket: 0, 20, 40, 60, 80, 100
    bracket = min(100, (belief // 20) * 20)

    # Time category: dawn/day/dusk/night
    h = wt["hour"]
    if 5 <= h < 8:
        time_cat = "dawn"
    elif 8 <= h < 17:
        time_cat = "day"
    elif 17 <= h < 21:
        time_cat = "dusk"
    else:
        time_cat = "night"

    return {
        "belief":          belief,
        "belief_bracket":  bracket,
        "nothing":         nothing,
        "hour":            h,
        "time_cat":        time_cat,
        "weather_raw":     wt["weather"],
        "temp_f":          wt["temp_f"],
        "moon":            wt["moon"],
        "arc_phase":       arc_phase,
        "arc_premise":     arc_premise,
        "stirred_npc":     npc,
    }


def state_signature(detail: dict) -> str:
    return f"{detail['belief_bracket']}_{detail['nothing']}_{detail['time_cat']}"


# ── Prompt construction ───────────────────────────────────────────────────────

# Fixed scene description — always the same room, same objects.
_SCENE = (
    "A student's dorm room inside a vast magical library-academy. Stone walls. "
    "A dark wooden desk in the foreground. On it: a sleek obsidian-black fountain pen "
    "with a dark nib — the Obsidian Chronograph — heavy and precise, slightly angled. "
    "Two small carved stone cats sit on a stack of weathered board games — one ginger-tinted, "
    "one charcoal-grey, their tails entwined. Round teal-framed spectacles rest on an open book. "
    "Teal-lens mirrors catch the light on the stone walls. "
    "A thick dark ribbed wool throw is draped over a reading chair."
)

_BELIEF_LIGHTING = {
    80: (
        "Warm golden amber fills the room. Three candles burn steadily. "
        "The stone cats have a faint luminous quality. A small plant blooms in the windowsill. "
        "The Chronograph's nib glints with dark ink."
    ),
    60: (
        "Comfortable warm lamplight. Two candles burning. "
        "The room feels lived-in and calm. Soft amber shadows."
    ),
    40: (
        "Softer, cooler light. One candle burning low. "
        "The stone cats sit still and dim. A faint coolness creeps into the corners."
    ),
    20: (
        "Dim, blue-grey light. Heavy shadows in the corners. "
        "One candle gutters. A plant on the windowsill has wilted. "
        "The Chronograph sits dry on the desk."
    ),
    10: (
        "Near-monochrome. Cold, flat light. "
        "The cats look like stone, not stone cats — inert. "
        "No warmth in the room except the faintest trace at the window."
    ),
    0: (
        "Almost fully desaturated — the entire room in shades of grey and white. "
        "Only a single candle flame retains its color: orange, stubborn, impossibly warm "
        "in an otherwise grey world."
    ),
}

_NOTHING_EFFECTS = {
    "healed":   "Clean, crisp linework throughout. Precise and vivid. No softening anywhere.",
    "low":      "Mostly crisp. One bookshelf in the deep background has a spine with no text on it.",
    "moderate": (
        "The far corners of the image soften very slightly — a watercolor wash bleeding toward white. "
        "Two or three book spines on the background shelf are blank, as if the ink faded."
    ),
    "high": (
        "Three corners of the scene are softening, dissolving toward white like watercolor in rain. "
        "A gap in the bookshelf where something used to stand. "
        "A chair near the far wall is slightly translucent — barely there."
    ),
    "critical": (
        "The edges of the image are actively dissolving — an invisible eraser working from outside in. "
        "The center remains vivid. The periphery is becoming white emptiness. "
        "Multiple blank spines on the shelves. The room feels like it is forgetting itself."
    ),
}

_NPC_TRACES = {
    "Zara":       "A folded note is visible, slid halfway under the door. Her handwriting on the outside.",
    "Boggle":     "A faint dusting of chalk near the window — she stopped by.",
    "Thorne":     "The Commonplace Book on the desk has been opened to a different page than before.",
    "Momort":     "A hand-drawn map, roughed out on a scrap of paper, has been left on the chair.",
    "Euphony":    "A small tuning fork rests on the windowsill, still faintly vibrating.",
    "Villanelle": "A scrap of paper near the Chronograph with one unfinished sentence.",
    "Stonebrook": "A cup of tea has been left on the desk. It is still warm.",
    "Wicker":     "One of the books on the desk has been moved — not where it was left.",
}

_ARC_ELEMENTS = {
    "SETUP": "In the background, barely visible: a second desk, empty but with a pencil still moving slowly across paper with no one there.",
    "RISING": "A faint trail of ink crosses the floor — footsteps leading toward the door, then stopping.",
    "CLIMAX": "The teal-lens mirrors on the wall are reflecting something that isn't quite what's in the room.",
    "FALLING": "One of the stone cats has turned its head — slightly, almost imperceptibly — toward the window.",
    "RESOLUTION": "The plant in the windowsill has a single new bloom on it, unexpected and exact.",
}


def build_window(weather_raw: str, hour: int, moon: str, temp_f: int) -> str:
    # Time of day light
    if hour < 5:
        light = "deep night sky, stars sharp and cold"
    elif hour < 8:
        light = "pre-dawn blue — the sky not yet decided"
    elif hour < 11:
        light = "morning light, long soft shadows, the day just beginning"
    elif hour < 15:
        light = "bright midday, clear hard light"
    elif hour < 18:
        light = "golden afternoon, angled warm light"
    elif hour < 21:
        light = "dusk — the sky deepening into indigo"
    else:
        light = "night, dark and deep"

    # Weather into ink-world
    w = weather_raw.lower()
    if any(x in w for x in ("heavy rain", "rain", "showers")):
        weather_desc = "ink-dark rivulets running down the glass in rivulets, the world outside smeared soft"
    elif any(x in w for x in ("drizzle", "mist", "fog")):
        weather_desc = "a grey mist, pages of fog drifting past the frame"
    elif any(x in w for x in ("snow", "blizzard")):
        weather_desc = "white pages drifting past the glass like something being erased"
    elif any(x in w for x in ("storm", "thunder", "lightning")):
        weather_desc = "ink-dark storm clouds pressing close, the window frame vibrating faintly"
    elif any(x in w for x in ("clear", "sunny", "fair")):
        weather_desc = "clear sky, crisp and exact"
        if hour >= 20:
            moon_str = re.sub(r"\(.*?\)", "", moon).strip()
            weather_desc += f", {moon_str} moon visible"
    elif any(x in w for x in ("overcast", "cloud", "grey", "gray")):
        weather_desc = "heavy sky the color of old paper, sitting on the rooftops"
    else:
        weather_desc = "the Academy grounds in deep quiet"

    # Temperature colour tinge
    if temp_f < 32:
        temp_note = "A faint frost-bloom on the inner corners of the glass."
    elif temp_f < 45:
        temp_note = "Cold emanating from the glass — you can feel it from here."
    else:
        temp_note = ""

    return f"Through the window: {light}. {weather_desc}. {temp_note}".strip().rstrip(".")


def build_prompt(detail: dict) -> str:
    bracket   = detail["belief_bracket"]
    # Find nearest lighting key
    lighting_key = max(k for k in _BELIEF_LIGHTING if k <= bracket)
    lighting  = _BELIEF_LIGHTING[lighting_key]
    nothing   = _NOTHING_EFFECTS[detail["nothing"]]
    window    = build_window(detail["weather_raw"], detail["hour"], detail["moon"], detail["temp_f"])
    npc_trace = _NPC_TRACES.get(detail["stirred_npc"], "")
    arc_el    = _ARC_ELEMENTS.get(detail["arc_phase"], _ARC_ELEMENTS["SETUP"])

    parts = [
        "Atmospheric dark anime illustration, Studio Ghibli meets Neil Gaiman aesthetic. "
        "Rich detailed linework. Deep atmospheric shadows. Painterly ink-washed backgrounds. "
        "No text, no UI elements, no labels.",
        "",
        f"SCENE: {_SCENE}",
        "",
        f"WINDOW: {window}.",
        "",
        f"ATMOSPHERE AND LIGHT: {lighting}",
        "",
        f"NOTHING EFFECT: {nothing}",
    ]

    if arc_el:
        parts += ["", f"SUBTLE STORY DETAIL (one quiet element in the background, not the focus): {arc_el}"]

    if npc_trace:
        parts += ["", f"NPC TRACE (a physical sign someone was here, ambient not focal): {npc_trace}"]

    parts += [
        "",
        "COMPOSITION: Landscape orientation, 16:9, for desktop wallpaper. "
        "The desk anchors the foreground. The window occupies the upper right. "
        "The room recedes into warm or cold shadow depending on atmosphere. "
        "The feeling is: someone lives here, and the world knows them.",
    ]

    return "\n".join(parts)


# ── Decision logic ────────────────────────────────────────────────────────────

def should_regenerate(sig: str, state: dict, force: bool = False) -> tuple[bool, str]:
    """Returns (should_regen, reason)."""
    if force:
        return True, "forced"

    last_gen  = state.get("last_generated", "")
    last_sig  = state.get("state_signature", "")
    hours_ago = hours_since(last_gen)

    if hours_ago > STALE_HOURS:
        return True, f"wallpaper is {hours_ago:.1f}h old (stale threshold: {STALE_HOURS}h)"

    if sig != last_sig and hours_ago >= COOLDOWN_HOURS:
        return True, f"state changed ({last_sig} → {sig})"

    if sig != last_sig and hours_ago < COOLDOWN_HOURS:
        return False, f"state changed but cooldown active ({hours_ago:.1f}h < {COOLDOWN_HOURS}h)"

    return False, f"state unchanged, wallpaper {hours_ago:.1f}h old"


# ── OS integration ────────────────────────────────────────────────────────────

def set_desktop_wallpaper(image_path: str) -> bool:
    """Set macOS desktop wallpaper via osascript."""
    abs_path = str(Path(image_path).resolve())
    script = (
        f'tell application "System Events" to set picture of every desktop to POSIX file "{abs_path}"'
    )
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        print(f"[wallpaper] Desktop set to: {abs_path}")
        return True
    else:
        print(f"[wallpaper] osascript failed: {result.stderr.strip()[:200]}")
        return False


def archive_image(src_path: str) -> str:
    """Copy image into wallpapers/ with timestamp name. Return new path."""
    WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y-%m-%d-%H-%M")
    ext  = Path(src_path).suffix or ".png"
    dest = WALLPAPER_DIR / f"{ts}{ext}"
    shutil.copy2(src_path, dest)
    return str(dest)


def cleanup_old(keep: int = ARCHIVE_KEEP) -> None:
    """Remove oldest wallpapers beyond the keep limit."""
    images = sorted(WALLPAPER_DIR.glob("????-??-??-??-??.*"))
    for old in images[:-keep]:
        old.unlink(missing_ok=True)


# ── Background generation via openclaw agent ──────────────────────────────────

def generate_via_agent(prompt: str, size: str = "1792x1024"):
    """
    Call the openclaw agent to generate the image.
    The agent must call image_generate and output the file path.
    Returns path string or None on failure.
    """
    msg = (
        f"Generate a desktop wallpaper image using the image_generate tool. "
        f"Use size=\"{size}\". Use this exact prompt — do not modify it:\n\n"
        f"{prompt}\n\n"
        f"After generating, output EXACTLY one line in this format and nothing else:\n"
        f"WALLPAPER_PATH: /full/path/to/saved/image.png"
    )

    result = subprocess.run(
        ["openclaw", "agent", "--local", "--agent", "enchantify", "-m", msg],
        capture_output=True, text=True, timeout=180
    )

    output = result.stdout.strip()
    # Strip ANSI
    output = re.sub(r'\x1b\[[0-9;]*m', '', output)

    # Try the explicit WALLPAPER_PATH marker first
    m = re.search(r'WALLPAPER_PATH:\s*(\S+)', output)
    if m:
        path = m.group(1).strip()
        if Path(path).exists():
            return path

    # Fall back: scan known openclaw image storage locations for the most recent PNG
    search_dirs = [
        Path.home() / ".openclaw" / "media" / "tool-image-generation",
        Path.home() / ".openclaw" / "media" / "generated",
        Path("/tmp"),
    ]
    candidates = []
    for d in search_dirs:
        if d.exists():
            candidates.extend(d.glob("*.png"))

    if candidates:
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        # Only use if it was created in the last 5 minutes
        age_minutes = (datetime.now().timestamp() - newest.stat().st_mtime) / 60
        if age_minutes < 5:
            print(f"[wallpaper] Found recent image at: {newest}")
            return str(newest)

    print(f"[wallpaper] Could not locate generated image. Agent output:\n{output[:400]}")
    return None


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_check(player_name: str, force: bool = False) -> None:
    """
    Print REGENERATE: YES/NO and prompt if yes.
    The Labyrinth reads this output at session open.
    """
    detail = get_game_detail(player_name)
    sig    = state_signature(detail)
    state  = load_state()
    regen, reason = should_regenerate(sig, state, force)

    print(f"REGENERATE: {'YES' if regen else 'NO'}")
    print(f"REASON: {reason}")
    print(f"STATE: {sig}")

    if regen:
        prompt = build_prompt(detail)
        print(f"\nWALLPAPER_SIZE: 1792x1024")
        print(f"\nWALLPAPER_PROMPT:\n{prompt}")
        print(f"\nEND_PROMPT")
        print(f"\nINSTRUCTION: Call image_generate with the above prompt and size. "
              f"Then run: python3 scripts/wallpaper.py --set [path]")


def cmd_set(image_path: str, player_name: str) -> None:
    """
    Called by Labyrinth after image_generate. Copies to archive, sets desktop, saves state.
    """
    if not Path(image_path).exists():
        print(f"[wallpaper] File not found: {image_path}")
        sys.exit(1)

    archived = archive_image(image_path)
    set_desktop_wallpaper(archived)
    cleanup_old()

    detail = get_game_detail(player_name)
    sig    = state_signature(detail)
    save_state(sig, archived, detail)
    print(f"[wallpaper] Done. Archived to {archived}")


def cmd_generate(player_name: str, force: bool = False) -> None:
    """Background generation — calls openclaw agent."""
    detail = get_game_detail(player_name)
    sig    = state_signature(detail)
    state  = load_state()
    regen, reason = should_regenerate(sig, state, force)

    if not regen:
        print(f"[wallpaper] No regeneration needed: {reason}")
        return

    print(f"[wallpaper] Generating ({reason})…")
    prompt = build_prompt(detail)
    path   = generate_via_agent(prompt)

    if path:
        cmd_set(path, player_name)
    else:
        print("[wallpaper] Generation failed — no path returned.")


def cmd_prompt(player_name: str) -> None:
    """Print the current prompt without generating."""
    detail = get_game_detail(player_name)
    sig    = state_signature(detail)
    print(f"State signature: {sig}")
    print(f"Belief: {detail['belief']} (bracket {detail['belief_bracket']})")
    print(f"Nothing: {detail['nothing']}")
    print(f"Time: {detail['time_cat']} (hour {detail['hour']})")
    print(f"Arc phase: {detail['arc_phase']}")
    print(f"Stirred NPC: {detail['stirred_npc'] or 'none'}")
    print(f"\n{'─'*60}\n{build_prompt(detail)}\n{'─'*60}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Academy desktop wallpaper")
    parser.add_argument("player",      nargs="?", default="bj")
    parser.add_argument("--check",     action="store_true",
                        help="Output REGENERATE: YES/NO + prompt if yes (Labyrinth reads this)")
    parser.add_argument("--set",       metavar="PATH",
                        help="Labyrinth calls this after image_generate with the file path")
    parser.add_argument("--generate",  action="store_true",
                        help="Background generation via openclaw agent")
    parser.add_argument("--force",     action="store_true",
                        help="Skip cooldown and state checks")
    parser.add_argument("--prompt",    action="store_true",
                        help="Print prompt only, no generation")
    args = parser.parse_args()

    if args.set:
        cmd_set(args.set, args.player)
    elif args.check:
        cmd_check(args.player, force=args.force)
    elif args.generate:
        cmd_generate(args.player, force=args.force)
    elif args.prompt:
        cmd_prompt(args.player)
    else:
        # Default: check (so `python3 scripts/wallpaper.py bj` is useful at a glance)
        cmd_check(args.player)


if __name__ == "__main__":
    main()
