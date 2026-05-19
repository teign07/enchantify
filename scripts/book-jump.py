#!/usr/bin/env python3
"""
book-jump.py — deterministic Book Jumping state machine.

The LLM supplies the wonder. This script owns the rails: book, anchor,
intention, depth, return count, Nothing degradation, souvenir due, and return.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
BOOKS = BASE / "lore" / "books.md"
STATE_DIR = PLAYERS
ARCHIVE_DIR = BASE / "memory" / "book-jumps"
LEDGER = BASE / "logs" / "book-jumps.jsonl"

START_COST = 1
RETURN_REWARD = 6
WONDER_COMPASS_REWARD = 18
MAX_DEPTH = 4


PUBLIC_DOMAIN_BOOKS = {
    "Peter Pan": {
        "world": "Neverland",
        "nothing": "the Lost Boys forgetting how to play",
        "arrival": "salt air, green shadow, and the alarming lightness of almost flying",
    },
    "The Wizard of Oz": {
        "world": "the yellow brick road",
        "nothing": "the Emerald City losing color into Kansas gray",
        "arrival": "dust, poppy sweetness, and color too bright to trust at first",
    },
    "Alice in Wonderland": {
        "world": "Wonderland",
        "nothing": "the nonsense making sense",
        "arrival": "warm cake, impossible angles, and a rule changing underfoot",
    },
    "The Odyssey": {
        "world": "the wine-dark sea",
        "nothing": "Odysseus forgetting what Ithaca looks like",
        "arrival": "salt, bronze, oar-rhythm, and homesickness with teeth",
    },
    "Pride and Prejudice": {
        "world": "drawing rooms, walks, letters, and social weather",
        "nothing": "the characters losing wit and becoming flatly functional",
        "arrival": "tea, wet lawn, candlewax, and a sentence with too much withheld",
    },
    "The Snow Queen": {
        "world": "snowfields and mirror-shards",
        "nothing": "a deeper cold freezing stories mid-sentence",
        "arrival": "blue-white cold, rose thorns, and the taste of a word on ice",
    },
    "Frankenstein": {
        "world": "laboratories, ice, and responsibility",
        "nothing": "the creature losing the desire to be understood",
        "arrival": "ozone, rain, old anatomy paper, and a hand wanting an answer",
    },
    "Dracula": {
        "world": "letters, castles, trains, and blood-warm dread",
        "nothing": "ink draining from the text until entries become illegible",
        "arrival": "iron, lavender, carriage leather, and a diary page breathing",
    },
    "A Christmas Carol": {
        "world": "London past, present, and possible",
        "nothing": "Scrooge forgetting what he learned",
        "arrival": "coal smoke, orange peel, frost, and a bell struck from inside memory",
    },
    "The Jungle Book": {
        "world": "the Law of the jungle",
        "nothing": "the jungle going silent",
        "arrival": "hot leaves, animal musk, dust, and a silence full of watching",
    },
    "Robin Hood": {
        "world": "Sherwood and the romance of outlaw justice",
        "nothing": "the Merry Men forgetting why they fight",
        "arrival": "oak leaves, rain-dark wool, bowstring wax, and laughter under cover",
    },
    "Don Quixote": {
        "world": "roads, inns, windmills, and dangerous Belief",
        "nothing": "Quixote becoming sane",
        "arrival": "dust, sun, old paper, and a giant where a mill should be",
    },
}

ORIGINAL_BOOKS = {
    "Clockwork Dreams and the Lost Key": "a clockwork city winding down",
    "The Whimsical Whodunit at Peculiar Manor": "a mansion mystery losing its clues",
    "The Astral Alchemist's Enigma": "a cosmic workshop whose stars are going out",
    "The Caper of the Constellation Cat": "a detective sky with stars missing",
    "Pirates of Pen & Parchment": "ink seas receding into blank parchment",
    "Festival of the Forgotten Fables": "forgotten folktales fading again",
    "The Atlas of Invisible Cities": "legendary cities becoming truly erased",
    "Chronicles of Great Inventors": "inventors losing their spark",
    "The Cosmic Observatory": "a telescope showing absence where stars belonged",
    "The Curious Case of the Vanishing Vowels": "language losing its vowels, then more",
    "The Symphony of Colorful Dreams": "dream-color draining to gray",
    "The Secret Society of Shadow Puppets": "shadows losing their shapes",
    "The Melody of Lost Memories": "memory melodies going silent",
    "The Quest for the Cosmic Teapot": "cosmic distance emptying into blankness",
}

WONDER_COMPASS_CHAPTERS = {
    "introduction": ("The sailboat. Belfast harbor, winter.", "the Rut arriving inside the dream life"),
    "read-this-first": ("A Tuesday. Anywhere.", "the precise quality of an unrecorded day"),
    "chapter1a": ("The dental practice.", "hands working while attention has vanished"),
    "chapter2": ("A planning session that goes nowhere.", "the Myth of the Mountain failing"),
    "chapter3": ("A dock at dusk. Amanda with a hula hoop.", "love nearby while presence is hard to reach"),
    "chapter4a": ("Inside the skull.", "the survival brain arguing with the wonder brain"),
    "chapter4b": ("A blank page. A permission slip.", "the choice to be inefficient and playful"),
    "chapter5": ("The first Compass Run.", "North, East, South, West, and the first souvenir"),
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_player(player: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", player or "bj") or "bj"


def state_path(player: str) -> Path:
    return STATE_DIR / f"{safe_player(player)}-book-jump.json"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "idle"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "idle", "invalid_previous_state": True}
    return data if isinstance(data, dict) else {"status": "idle"}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_state(player: str) -> dict[str, Any]:
    return read_json(state_path(player))


def save_state(player: str, data: dict[str, Any]) -> None:
    write_json(state_path(player), data)


def append_ledger(event: str, player: str, payload: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": now(), "event": event, "player": player, **payload}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def compact(text: str, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "book-jump"


def update_belief(player: str, delta: int, dry_run: bool = False) -> None:
    if dry_run or delta == 0:
        return
    subprocess.run(
        [sys.executable, str(BASE / "scripts" / "update-player.py"), player, "belief", f"{delta:+d}"],
        cwd=BASE,
        check=True,
    )


def book_profile(title: str, chapter: str = "") -> dict[str, str]:
    title = title.strip()
    if title.lower() in {"wonder compass", "the wonder compass"}:
        key = (chapter or "chapter5").lower().replace(" ", "-")
        location, witness = WONDER_COMPASS_CHAPTERS.get(key, WONDER_COMPASS_CHAPTERS["chapter5"])
        return {
            "title": "The Wonder Compass",
            "kind": "wonder-compass-memory",
            "world": location,
            "nothing": "forgetting why the Compass was built",
            "arrival": f"memory-weather: {witness}",
            "rules": "Witness only. The player cannot change events; they can stay present and name a souvenir.",
            "chapter": key,
        }
    if title in PUBLIC_DOMAIN_BOOKS:
        data = PUBLIC_DOMAIN_BOOKS[title]
        return {"title": title, "kind": "public-domain", **data, "rules": "Interact as yourself. Do not replace the protagonist."}
    if title in ORIGINAL_BOOKS:
        return {
            "title": title,
            "kind": "labyrinth-original",
            "world": ORIGINAL_BOOKS[title],
            "nothing": "the book's central wonder thinning into blankness",
            "arrival": "fresh ink, unstable genre-weather, and a door that knows it was just written",
            "rules": "Original Labyrinth book. The world can answer Enchantify mechanics directly.",
        }
    return {
        "title": title,
        "kind": "unknown",
        "world": "unverified shelf territory",
        "nothing": "unmapped textual degradation",
        "arrival": "unclassified ink-weather",
        "rules": "Do not enter deeply until a professor verifies this title.",
    }


def directive(state: dict[str, Any], instruction: str) -> None:
    print("BOOK_JUMP_DIRECTIVE")
    print(f"STATUS: {state.get('status', 'idle')}")
    if state.get("title"):
        print(f"BOOK: {state.get('title')}")
        print(f"KIND: {state.get('kind')}")
        print(f"WORLD: {state.get('world')}")
        print(f"ANCHOR: {state.get('anchor')}")
        print(f"INTENTION: {state.get('intention')}")
        print(f"GUIDE: {state.get('guide')}")
        print(f"DEPTH: {state.get('depth', 0)}/{MAX_DEPTH}")
        print(f"RETURN_COUNT: {state.get('return_count', 0)}")
        print(f"DEGRADATION: {state.get('degradation', 0)}")
        print(f"NOTHING: {state.get('nothing')}")
        print(f"SOUVENIR_DUE: {state.get('souvenir_due', False)}")
    print(f"SCENE_INSTRUCTION: {instruction}")
    print("HARD_RULES: Narrate one beat only. The player remains themselves. Do not complete the jump or return without this script. If Nothing pressure rises, require a formal Enchantment, Compass proof, or emergency return.")


def cmd_start(args: argparse.Namespace) -> int:
    current = load_state(args.player)
    if current.get("status") == "active" and not args.force:
        raise SystemExit(f"Book Jump already active: {current.get('title')} depth {current.get('depth')}. Use status/advance/return or --force.")
    profile = book_profile(args.book, args.chapter)
    state = {
        "status": "active",
        "started_at": now(),
        "updated_at": now(),
        "player": args.player,
        "title": profile["title"],
        "kind": profile["kind"],
        "chapter": profile.get("chapter", ""),
        "world": profile["world"],
        "nothing": profile["nothing"],
        "arrival": profile["arrival"],
        "rules": profile["rules"],
        "anchor": args.anchor,
        "intention": args.intention,
        "guide": args.guide,
        "depth": 0,
        "return_count": int(args.return_count),
        "degradation": 0,
        "souvenir_due": False,
        "events": [],
        "cost": START_COST,
    }
    if not args.dry_run:
        update_belief(args.player, -START_COST)
        save_state(args.player, state)
        append_ledger("start", args.player, state)
    directive(state, f"Open the book jump. Show the book, the anchor, the intention, and the first sensory pull. Do not land deeper than arrival threshold. Cost: -{START_COST} Belief.")
    print(f"ARRIVAL_TEXTURE: {profile['arrival']}")
    print(f"BOOK_RULES: {profile['rules']}")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    state = load_state(args.player)
    if state.get("status") != "active":
        raise SystemExit("No active Book Jump. Use start first.")
    depth = min(MAX_DEPTH, int(state.get("depth", 0)) + 1)
    degradation = int(state.get("degradation", 0))
    if args.nothing:
        degradation += 1
    elif depth >= 3:
        degradation += 1
    event = {
        "at": now(),
        "beat": args.beat or f"depth-{depth}",
        "depth": depth,
        "degradation": degradation,
    }
    state["depth"] = depth
    state["degradation"] = degradation
    state["updated_at"] = now()
    state.setdefault("events", []).append(event)
    if depth >= 2:
        state["souvenir_due"] = True
    save_state(args.player, state)
    append_ledger("advance", args.player, event | {"title": state.get("title")})
    instruction = "Advance exactly one beat inside the book. Keep the player embodied, in Academy robes, with their pen. "
    if degradation:
        instruction += "Show textual degradation as the Nothing thinning the book; do not resolve it without a formal action. "
    if state.get("souvenir_due"):
        instruction += "Begin making one sensory souvenir possible, but do not invent the player's souvenir sentence."
    directive(state, instruction)
    return 0


def cmd_stabilize(args: argparse.Namespace) -> int:
    state = load_state(args.player)
    if state.get("status") != "active":
        raise SystemExit("No active Book Jump to stabilize.")
    old = int(state.get("degradation", 0))
    new = max(0, old - 1)
    state["degradation"] = new
    state["updated_at"] = now()
    state.setdefault("events", []).append({"at": now(), "beat": "stabilize", "method": args.method, "degradation": new})
    save_state(args.player, state)
    append_ledger("stabilize", args.player, {"title": state.get("title"), "method": args.method, "before": old, "after": new})
    directive(state, f"Stabilize the jump using the confirmed method: {args.method}. Narrate how the book regains detail. Do not deepen the jump in the same reply.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state(args.player)
    directive(state, "Report current Book Jump state. If active, continue from this exact book, depth, degradation, anchor, guide, and souvenir due flag.")
    return 0


def archive_return(player: str, state: dict[str, Any], souvenir: str, outcome: str) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    title = state.get("title", "book-jump")
    path = ARCHIVE_DIR / f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-{slug(title)}.md"
    lines = [
        f"# Book Jump: {title}",
        "",
        f"- **Player:** {player}",
        f"- **Started:** {state.get('started_at', '')}",
        f"- **Returned:** {now()}",
        f"- **Kind:** {state.get('kind', '')}",
        f"- **Anchor:** {state.get('anchor', '')}",
        f"- **Intention:** {state.get('intention', '')}",
        f"- **Guide:** {state.get('guide', '')}",
        f"- **Depth:** {state.get('depth', 0)}",
        f"- **Return Count:** {state.get('return_count', 0)}",
        f"- **Degradation:** {state.get('degradation', 0)}",
        f"- **Outcome:** {outcome}",
        "",
        "## Souvenir",
        souvenir.strip(),
        "",
        "## Beats",
    ]
    for event in state.get("events", []):
        lines.append(f"- {event.get('at', '')}: {event.get('beat', '')} (depth {event.get('depth', '?')}, degradation {event.get('degradation', '?')})")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def cmd_return(args: argparse.Namespace) -> int:
    state = load_state(args.player)
    if state.get("status") != "active":
        raise SystemExit("No active Book Jump to return from.")
    souvenir = (args.souvenir or "").strip()
    if not args.emergency and len(souvenir) < 12:
        raise SystemExit("Return requires a real souvenir sentence unless --emergency is used.")
    reward = 0 if args.emergency else (WONDER_COMPASS_REWARD if state.get("kind") == "wonder-compass-memory" else RETURN_REWARD)
    if reward:
        update_belief(args.player, reward)
    state["status"] = "returned"
    state["returned_at"] = now()
    state["outcome"] = args.outcome
    state["souvenir"] = souvenir
    archive = archive_return(args.player, state, souvenir or "(emergency return; souvenir deferred)", args.outcome)
    append_ledger("return", args.player, {"title": state.get("title"), "reward": reward, "archive": str(archive), "emergency": args.emergency})
    state_path(args.player).unlink(missing_ok=True)
    directive(state, f"Return through the Spine. Narrate the text dissolving and the Academy re-forming around the player. Reward: +{reward} Belief. Archive: {archive.relative_to(BASE)}")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    state = load_state(args.player)
    state_path(args.player).unlink(missing_ok=True)
    append_ledger("cancel", args.player, {"previous": state, "reason": args.reason})
    print("BOOK_JUMP_CANCELLED")
    print(f"REASON: {args.reason}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    print("BOOK_JUMP_LIBRARY")
    print("PUBLIC_DOMAIN: " + "; ".join(PUBLIC_DOMAIN_BOOKS))
    print("ORIGINAL_LABYRINTH: " + "; ".join(ORIGINAL_BOOKS))
    print("SPECIAL: The Wonder Compass chapters: " + "; ".join(WONDER_COMPASS_CHAPTERS))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Book Jumping state machine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("start")
    p.add_argument("player")
    p.add_argument("--book", required=True)
    p.add_argument("--anchor", default="the open page")
    p.add_argument("--intention", default="learn what this text is asking")
    p.add_argument("--guide", default="Professor Archibald Permancer")
    p.add_argument("--return-count", type=int, default=3)
    p.add_argument("--chapter", default="")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("advance")
    p.add_argument("player")
    p.add_argument("--beat", default="")
    p.add_argument("--nothing", action="store_true")
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("stabilize")
    p.add_argument("player")
    p.add_argument("--method", required=True)
    p.set_defaults(func=cmd_stabilize)

    p = sub.add_parser("return")
    p.add_argument("player")
    p.add_argument("--souvenir", default="")
    p.add_argument("--outcome", default="returned with a named fragment")
    p.add_argument("--emergency", action="store_true")
    p.set_defaults(func=cmd_return)

    p = sub.add_parser("status")
    p.add_argument("player")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("cancel")
    p.add_argument("player")
    p.add_argument("--reason", default="manual cancellation")
    p.set_defaults(func=cmd_cancel)

    p = sub.add_parser("list")
    p.set_defaults(func=cmd_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
