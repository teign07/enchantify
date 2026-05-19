#!/usr/bin/env python3
"""
scene_packet_builder.py — build a lightweight ScenePacket from the current
Enchantify scene spine without replacing it.

Normal live runs should enter through scripts/run-live-scene.py,
which calls play_scene.py, which calls this builder.

This is glue, not a new source of truth.
It reads the existing scene-director/session-entry outputs and wraps a finished
scene into a conductor-ready packet.

Usage:
  python3 scripts/scene_packet_builder.py bj --text-file /tmp/scene.txt
  python3 scripts/scene_packet_builder.py bj --text-file /tmp/scene.txt --voice-file /tmp/voice.txt --out /tmp/scene.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
DEFAULT_TARGET = "8729557865"
TOOL_STATE_FILE = Path(os.environ.get("ENCHANTIFY_TOOL_STATE", BASE / "memory" / "page-tool-state.json"))
PLAYER_DIR = BASE / "players"
sys.path.insert(0, str(BASE / "mechanics"))
import mechanics_state  # type: ignore


_CHARACTER_VISUALS_MODULE = None


def character_visuals_module():
    global _CHARACTER_VISUALS_MODULE
    if _CHARACTER_VISUALS_MODULE is not None:
        return _CHARACTER_VISUALS_MODULE
    path = SCRIPTS / "character-visuals.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("character_visuals", path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CHARACTER_VISUALS_MODULE = module
    return module


def run_script(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_tool_state() -> dict:
    if not TOOL_STATE_FILE.exists():
        return {}
    try:
        return json.loads(TOOL_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_tool_state(state: dict) -> None:
    TOOL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = TOOL_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(TOOL_STATE_FILE)


def hours_since(iso: str | None) -> float:
    if not iso:
        return 9999.0
    try:
        return (datetime.now() - datetime.fromisoformat(iso)).total_seconds() / 3600
    except Exception:
        return 9999.0


def gate_page_tools(sequence: list[str], page_type: str, tool_posture: dict, state: dict) -> tuple[list[str], list[dict]]:
    cooldowns = tool_posture.get("cooldowns") or {}
    gated = {"lights", "music", "spotify", "printer", "wallpaper", "app_actions"}
    kept: list[str] = []
    suppressed: list[dict] = []
    for step in sequence:
        cooldown = cooldowns.get(step)
        key = f"{page_type}:{step}"
        if step in gated and cooldown is not None:
            age = hours_since((state.get(key) or {}).get("last_used_at"))
            if age < float(cooldown):
                suppressed.append({
                    "tool": step,
                    "reason": f"cooldown active ({age:.1f}h < {cooldown}h)",
                    "key": key,
                })
                continue
        kept.append(step)
    return kept, suppressed


def mark_page_tools_used(sequence: list[str], page_type: str, state: dict) -> None:
    now = datetime.now().isoformat()
    for step in sequence:
        if step in {"lights", "music", "spotify", "printer", "wallpaper", "app_actions"}:
            state[f"{page_type}:{step}"] = {"last_used_at": now}


def page_app_actions(page_type: str, title: str, scene_text: str) -> list[dict]:
    scene_hint = re.sub(r"\s+", " ", scene_text).strip()[:220]
    today = datetime.now().strftime("%Y-%m-%d")
    if page_type == "conflict":
        return [{
            "driver": "apple_reminders",
            "action": "create_reminder",
            "chapter": "Duskthorn",
            "title": f"Enchantify: {title[:60]}",
            "notes": f"The page left pressure behind: {scene_hint}",
        }]
    if page_type == "letter":
        return [{
            "driver": "apple_notes",
            "action": "create_note",
            "chapter": "Mossbloom",
            "title": f"Letter Page — {today}",
            "body": f"A letter arrived from the Labyrinth.\n\n{scene_hint}\n\nKeep the proof.",
        }]
    if page_type == "archive":
        return [{
            "driver": "obsidian",
            "action": "append_to_daily",
            "chapter": "Mossbloom",
            "content": f"Enchantify archived a page: {scene_hint}",
        }]
    if page_type == "rest":
        return [{
            "driver": "obsidian",
            "action": "append_to_daily",
            "chapter": "Mossbloom",
            "content": "Rest counted as a real page. Nothing was owed for stopping.",
        }]
    return []


def parse_slate_value(slate: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", slate, re.MULTILINE)
    return m.group(1).strip() if m else ""


def player_visual_fragment(player: str, scene_text: str) -> str:
    path = PLAYER_DIR / f"{player}.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    gender = re.search(r"^\s*-\s+\*\*Gender Identity:\*\*\s*(.+)$", text, re.MULTILINE)
    appearance = re.search(r"^\s*-\s+\*\*Appearance:\*\*\s*(.+)$", text, re.MULTILINE)
    traits = re.search(r"^\s*-\s+\*\*Traits:\*\*\s*(.+)$", text, re.MULTILINE)
    chapter = re.search(r"^\s*-\s+\*\*Chapter:\*\*\s*(.+)$", text, re.MULTILINE)
    belief = re.search(r"^\s*-\s+\*\*Belief:\*\*\s*(.+)$", text, re.MULTILINE)
    parts = []
    if gender:
        parts.append(f"PLAYER GENDER IDENTITY for BJ / the player: {gender.group(1).strip()}")
    else:
        parts.append("PLAYER GENDER IDENTITY for BJ / the player: male; adult man; he/him visual presentation.")
    if appearance:
        parts.append(f"PLAYER VISUAL IDENTITY for BJ / the player: {appearance.group(1).strip()}")
    if chapter:
        parts.append(f"Chapter palette/context: {chapter.group(1).strip()}.")
    if traits:
        parts.append(f"Personality cues: {traits.group(1).strip()}")
    if belief:
        parts.append(f"Belief presence: {belief.group(1).strip()}.")
    if not parts:
        return ""
    if re.search(r"\b(you|your|bj)\b", scene_text, re.IGNORECASE):
        parts.append("If the player is visible, preserve these identifiers across live-scene illustrations. Do not depict BJ/the player as female, feminine-presenting, a girl, or a woman unless the player explicitly changes identity.")
    return " ".join(parts)


def visual_name_aliases(name: str) -> list[str]:
    aliases = [name]
    extra = {
        "Headmistress Seraphina Thorne": ["Headmistress Thorne", "Thorne"],
        "Professor Cedric Stonebrook": ["Professor Stonebrook", "Stonebrook"],
        "Professor Lydia Boggle": ["Professor Boggle", "Boggle"],
        "Dr. Elowen Vellum": ["Dr. Vellum", "Vellum"],
        "Dr. Selene Inkrest": ["Dr. Inkrest", "Inkrest"],
    }
    aliases.extend(extra.get(name, []))
    return aliases


def mentioned_visual_characters(cast: str, scene_text: str, title: str) -> list[str]:
    module = character_visuals_module()
    if not module:
        return []
    try:
        visuals = BASE / "lore" / "character-visuals.json"
        sources = [BASE / "lore" / "characters.md", BASE / "lore" / "world-register.md"]
        stale = (
            not visuals.exists()
            or any(path.exists() and path.stat().st_mtime > visuals.stat().st_mtime for path in sources)
        )
        if stale:
            module.sync()
        data = module.load_visuals()
    except Exception:
        return []
    characters = data.get("characters") or {}
    haystack = f" {cast or ''} {title or ''} {scene_text or ''} ".lower()
    found: list[tuple[int, str]] = []
    for name in characters:
        for alias in visual_name_aliases(name):
            needle = alias.lower()
            if not needle:
                continue
            pos = haystack.find(needle)
            if pos >= 0:
                found.append((pos, name))
                break
    found.sort(key=lambda item: item[0])
    deduped: list[str] = []
    for _pos, name in found:
        if name not in deduped:
            deduped.append(name)
    return deduped


def character_focus_from_scene(cast: str, scene_text: str, title: str) -> str:
    if re.search(r"\b(you|your|bj)\b", f" {title or ''} {scene_text or ''} ", re.IGNORECASE):
        player_first = re.search(r"\b(you|your|bj)\b", f" {title or ''} {scene_text or ''} ", re.IGNORECASE)
        first_npc = mentioned_visual_characters(cast, scene_text, title)
        if not first_npc or (player_first and player_first.start() < f' {title or ""} {scene_text or ""} '.lower().find(first_npc[0].lower())):
            return "BJ / the player"
    visual_mentions = mentioned_visual_characters(cast, scene_text, title)
    if visual_mentions:
        return visual_mentions[0]
    text = " ".join([cast or "", scene_text or "", title or ""])
    candidates: list[str] = []
    for match in re.finditer(r"\b(?:Professor|Headmistress|Dr\.)\s+[A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+)?", text):
        candidates.append(match.group(0).strip())
    for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+\"[A-Z][A-Za-z'’-]+\")?\s+[A-Z][A-Za-z'’-]+", text):
        name = match.group(0).strip()
        if name not in {"The Nothing", "The Academy", "The Bleed"}:
            candidates.append(name)
    for name in candidates:
        if len(name) <= 60:
            return name
    return "the most emotionally important character in the scene"


def character_visual_fragment(name: str) -> str:
    if name == "BJ / the player":
        return player_visual_fragment("bj", "BJ")
    module = character_visuals_module()
    if not module or not name or name == "the most emotionally important character in the scene":
        return ""
    try:
        visuals = BASE / "lore" / "character-visuals.json"
        sources = [BASE / "lore" / "characters.md", BASE / "lore" / "world-register.md"]
        stale = (
            not visuals.exists()
            or any(path.exists() and path.stat().st_mtime > visuals.stat().st_mtime for path in sources)
        )
        if stale:
            module.sync()
        return module.prompt_fragment(name)
    except Exception:
        return ""


def scene_visual_fragments(player: str, cast: str, scene_text: str, title: str, focus: str = "") -> tuple[str, list[str]]:
    fragments: list[str] = []
    names: list[str] = []
    player_fragment = player_visual_fragment(player, scene_text)
    if player_fragment and focus != "BJ / the player":
        fragments.append(player_fragment)
        names.append("BJ / the player")
    for name in mentioned_visual_characters(cast, scene_text, title)[:5]:
        if name == focus:
            continue
        fragment = character_visual_fragment(name)
        if fragment:
            fragments.append(fragment)
            names.append(name)
    return " ".join(fragments), names


def build_image_prompt(title: str, mood: str, feel: str, cast: str, scene_text: str, player: str = "bj") -> str:
    scene_hint = scene_text.replace("\n", " ").strip()
    scene_hint = re.sub(r"\s+", " ", scene_hint)
    scene_hint = scene_hint[:260]
    focus = character_focus_from_scene(cast, scene_text, title)
    visual_identity = character_visual_fragment(focus)
    cast_visuals, visual_names = scene_visual_fragments(player, cast, scene_text, title, focus)
    if visual_identity and focus not in visual_names:
        visual_names.insert(0, focus)
    cast_hint = cast[:120] if cast else "current scene cast"
    feel_hint = feel[:120] if feel else mood
    style = (
        "illustrated in sparse pen-and-ink linework with loose watercolor washes on textured aged parchment, "
        "with visible paper grain, soft ink bleed, watercolor blooms, layered manuscript-page composition, "
        "lush handwritten marginalia, lush watercolor washes, visible library stamps, wax seals, labels, tabs, arrows, "
        "annotations, archival overlays, and selective pops of color. Make the page furniture abundant and integral, "
        "not timid decoration. Keep the image airy, literary, sketch-like, "
        "and slightly unfinished, like a page from a magical field journal rather than a polished digital illustration. "
        "Include generous page layout elements such as notes, labels, sketches, margin writing, stamps, seals, and overlays so "
        "the image feels embedded in a manuscript page"
    )
    return (
        f"Character-focused field-journal portrait of {focus}. "
        f"{visual_identity + ' ' if visual_identity else ''}"
        f"{cast_visuals + ' ' if cast_visuals else ''}"
        f"The image may focus on one character, but any character it shows must use their provided visual identity. "
        f"Do not redesign BJ/the player or named NPCs. If BJ/the player appears, depict him as a male adult man according to his Gender Identity and Appearance fields. "
        f"Canonical character pool: {', '.join(visual_names) if visual_names else focus}. "
        f"Prefer one clear focal figure unless the scene explicitly needs two. Show face, expression, posture, hands, clothing details, and one meaningful object or gesture. "
        f"Mood: {mood}; atmosphere: {feel_hint}; supporting cast context: {cast_hint}. "
        f"Story beat to embody through the character: {scene_hint}. "
        "Keep architecture as a faint background wash only; do not make the room, corridor, library, door, desk, or landscape the subject. "
        f"{style}. No UI elements, no caption, no watermark."
    )


def build_music_prompt(title: str, mood: str, feel: str, story: str, schedule: str) -> str:
    parts = [title, mood, feel, story, schedule]
    text = ", ".join(p for p in parts if p)
    text = re.sub(r"\s+", " ", text).strip()
    return f"Short instrumental scene cue, {text}, magical library atmosphere, cinematic but intimate, no vocals."


def apply_page_tool_posture(
    packet: dict,
    scene_contract: dict,
    title: str,
    mood: str,
    feel: str,
    cast: str,
    story: str,
    schedule: str,
    scene_text: str,
    scene_id: str,
    requested_intensity: str,
) -> None:
    suggestion = scene_contract.get("tool_packet_suggestion") or {}
    page_contract = scene_contract.get("page_contract") or {}
    tool_posture = page_contract.get("tool_posture") or {}
    if not suggestion.get("sequence"):
        packet.setdefault("metadata", {})["tool_authority"] = "global-intensity-fallback"
        packet.setdefault("metadata", {})["tool_warning"] = (
            "No Page tool posture was available; legacy intensity sequence was used."
        )
        return

    page_type = page_contract.get("page_type") or "unknown"
    tool_state = load_tool_state()
    sequence, suppressed = gate_page_tools(list(suggestion.get("sequence")), page_type, tool_posture, tool_state)
    if "text" not in sequence:
        sequence.insert(0, "text")
    if "voice" not in sequence:
        sequence.append("voice")
    packet["sequence"] = sequence
    packet["intensity"] = suggestion.get("intensity") or requested_intensity
    metadata = packet.setdefault("metadata", {})
    metadata["tool_authority"] = "page-tool-posture"
    metadata["page_type"] = page_type
    metadata["page_label"] = page_contract.get("page_label")
    metadata["tool_posture"] = tool_posture.get("posture")
    metadata["intrusion_level"] = tool_posture.get("intrusion_level", "low")
    metadata["audio_roles"] = tool_posture.get("audio_roles", {})
    metadata["artifact_tools"] = tool_posture.get("artifact_tools", [])
    metadata["suppressed_tools"] = suppressed
    metadata["legacy_intensity_requested"] = requested_intensity

    if "image" in packet["sequence"]:
        packet["image"] = {
            "prompt": build_image_prompt(title, mood, feel, cast, scene_text, packet["metadata"].get("player", "bj")),
            "filename_hint": f"{scene_id}.png",
            "backend": "drawthings",
            "deliver": True,
        }
    else:
        packet.pop("image", None)

    light_hint = suggestion.get("lights")
    if "lights" in packet["sequence"] and light_hint:
        packet["lights"] = light_hint
    else:
        packet.pop("lights", None)

    if "music" in packet["sequence"]:
        packet["music"] = {
            "prompt": build_music_prompt(title, mood, feel, story, schedule),
            "instrumental": True,
            "duration_seconds": int((suggestion.get("music") or {}).get("duration_seconds") or 20),
            "deliver": bool((suggestion.get("music") or {}).get("deliver", False)),
        }
    else:
        packet.pop("music", None)

    if "spotify" in packet["sequence"]:
        packet["spotify"] = {
            "mood": (suggestion.get("spotify") or {}).get("mood") or mood,
            "action": (suggestion.get("spotify") or {}).get("action") or "mood_only",
            "chapter": infer_spotify_chapter(mood, story, feel),
            "tier": "Sovereign" if packet["intensity"] == "ritual" else "Influenced",
        }
    else:
        packet.pop("spotify", None)

    if "printer" in packet["sequence"]:
        packet["printer"] = {
            "artifact_type": (suggestion.get("printer") or {}).get("artifact_type") or "page-artifact",
            "content": (suggestion.get("printer") or {}).get("content_hint") or "Page artifact pending final scene proof.",
            "filename_hint": f"{scene_id}-artifact.txt",
        }
    else:
        packet.pop("printer", None)

    if "wallpaper" in packet["sequence"]:
        packet["wallpaper"] = {
            "action": "brief",
            "player": packet["metadata"].get("player", "bj"),
            "reason": (suggestion.get("wallpaper") or {}).get("prompt_hint") or "Page-significant wallpaper shift",
            "command_hint": f"python3 scripts/wallpaper.py --generate {packet['metadata'].get('player', 'bj')}",
        }
    else:
        packet.pop("wallpaper", None)

    if "app_actions" in packet["sequence"]:
        packet["app_actions"] = {
            "mode": "brief",
            "allowed_private_apps": (suggestion.get("app_actions") or {}).get("allowed_private_apps", []),
            "public_apps_require_consent": True,
            "content_hint": (suggestion.get("app_actions") or {}).get("content_hint") or "private Page artifact",
            "actions": page_app_actions(page_type, title, scene_text),
        }
    else:
        packet.pop("app_actions", None)

    mark_page_tools_used(packet["sequence"], page_type, tool_state)
    save_tool_state(tool_state)


def title_from_scene_text(scene_text: str) -> str:
    for line in scene_text.splitlines():
        line = line.strip().strip("*")
        if not line or line.startswith("["):
            continue
        line = re.sub(r"\s+", " ", line)
        sentence = re.split(r"(?<=[.!?])\s+", line)[0]
        words = sentence.split()
        if len(words) > 12:
            sentence = " ".join(words[:12])
        return sentence[:90].rstrip(".,;:")
    return "Enchantify scene"


def clean_title(candidate: str, scene_text: str) -> str:
    title = (candidate or "").strip()
    if not title:
        return title_from_scene_text(scene_text)
    operational = (
        "session closed cleanly",
        "fixing",
        "scripts/",
        ".py",
        "bug",
        "hard rule now lives",
    )
    if any(item in title.lower() for item in operational):
        return title_from_scene_text(scene_text)
    return title[:110].rstrip(".,;:")


def infer_spotify_chapter(mood: str, story: str, feel: str) -> str:
    joined = " ".join([mood, story, feel]).lower()
    if any(k in joined for k in ["conflict", "thorn", "pressure", "tense", "wrong"]):
        return "Duskthorn"
    if any(k in joined for k in ["together", "friend", "shared", "collaborative"]):
        return "Riddlewind"
    if any(k in joined for k in ["still", "quiet", "gentle", "receive", "moss"]):
        return "Mossbloom"
    if any(k in joined for k in ["surge", "now", "wave", "bright", "alive"]):
        return "Tidecrest"
    return "Emberheart"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--voice-file", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--mood")
    parser.add_argument("--scene-mode", choices=["slice", "school-life", "arc", "mystery", "aftermath", "compass", "enchantment"])
    parser.add_argument("--drama-budget", choices=["low", "medium", "high"])
    parser.add_argument("--intensity", default="cinematic")
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--channel", default="telegram")
    parser.add_argument("--account", default="enchantify")
    args = parser.parse_args()

    scene_text = read_text(args.text_file)
    if not scene_text:
        print("text file missing or empty", file=sys.stderr)
        return 1

    voice_text = read_text(args.voice_file) or f"[bm_lewis] {scene_text}"
    slate = run_script([sys.executable, str(SCRIPTS / "scene-director.py"), args.player, "--slate-only"])
    entry = run_script([sys.executable, str(SCRIPTS / "session-entry.py"), args.player])

    cast = parse_slate_value(slate, "CAST")
    feel = parse_slate_value(slate, "FEEL")
    story = parse_slate_value(slate, "STORY")
    schedule = parse_slate_value(slate, "SCHEDULE")

    title = args.title or parse_slate_value(slate, "SCENE_ANCHOR") or ""
    title = clean_title(title.split("|")[0].strip() if title else "", scene_text)
    mood = args.mood or parse_slate_value(slate, "FEEL") or "living library atmosphere"

    preflight_status = mechanics_state.get_preflight_status(BASE, args.player)
    contract_cmd = [sys.executable, str(SCRIPTS / "scene-contract.py"), args.player, "--json"]
    if args.scene_mode:
        contract_cmd += ["--mode", args.scene_mode]
    if args.drama_budget:
        contract_cmd += ["--drama-budget", args.drama_budget]
    contract_text = run_script(contract_cmd)
    try:
        scene_contract = json.loads(contract_text) if contract_text else {}
    except json.JSONDecodeError:
        scene_contract = {}

    scene_id = f"scene-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    packet = {
        "scene_id": scene_id,
        "title": title,
        "mood": mood,
        "intensity": args.intensity,
        "target": args.target,
        "channel": args.channel,
        "account": args.account,
        "routing_model": "claude-cli/claude-haiku-4-5",
        "text": {
            "text": scene_text,
        },
        "voice": {
            "text": voice_text,
        },
        "metadata": {
            "player": args.player,
            "director_slate": slate,
            "session_entry": entry,
            "cast": cast,
            "feel": feel,
            "story": story,
            "schedule": schedule,
            "preserve_scene_construction": True,
            "source_systems": ["session-entry", "scene-director", "narrative-scene"],
            "mechanics_preflight": preflight_status,
            "scene_contract": scene_contract,
        },
    }
    apply_page_tool_posture(
        packet,
        scene_contract,
        title,
        mood,
        feel,
        cast,
        story,
        schedule,
        scene_text,
        scene_id,
        args.intensity,
    )

    out = args.out or (BASE / "tmp" / "scene-outbox" / f"{scene_id}-packet.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
