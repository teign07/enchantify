#!/usr/bin/env python3
"""Canonical Enchantment ritual runner.

This script exists so an Enchantment cannot collapse into prose. It handles the
formal phases: offer, start/cost, completion/reward, decline, and status.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MECHANICS = BASE / "mechanics"
if str(MECHANICS) not in sys.path:
    sys.path.insert(0, str(MECHANICS))
import mechanics_state  # type: ignore

SESSION_DIR = BASE / "players"
LEDGER = BASE / "logs" / "enchantments.jsonl"
BELIEF_COST = 3
BELIEF_REWARD = 9
IMAGE_DIR = BASE / "memory" / "enchantments" / "images"
VISUAL_ENCHANTMENTS = {
    "Everything's Van Gogh": (
        "Vincent van Gogh inspired post-impressionist painting, expressive swirling brushwork, thick impasto texture, luminous yellows and cobalt blues, emotionally charged sky and contours",
        "van-gogh",
    ),
    "Everything's Monet": (
        "Claude Monet inspired impressionist painting, soft broken color, plein-air light, shimmering atmosphere, loose brushwork, luminous reflections, gentle blurred edges",
        "monet",
    ),
    "Everything's Anime": (
        "expressive hand-drawn anime key art, clean characterful linework, cinematic composition, luminous color, emotional atmosphere, rich background detail",
        "anime",
    ),
    "Everything's Shakespeare": (
        "Renaissance theatrical manuscript illustration, dramatic chiaroscuro, velvet shadows, ornate stage-like composition, sonnet marginalia, Elizabethan pageantry",
        "shakespeare",
    ),
    "Everything's Archive": (
        "magical field-journal manuscript page, sparse pen-and-ink linework, lush watercolor washes on textured aged parchment, abundant handwritten marginalia, library stamps, wax seals, labels, tabs, arrows, archival overlays",
        "archive",
    ),
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def session_path(player: str) -> Path:
    return SESSION_DIR / f"{player}-session.json"


def load_session(player: str) -> dict:
    data = read_json(session_path(player))
    if not isinstance(data, dict):
        data = {}
    mechanics = data.setdefault("mechanics", {})
    enchantment = mechanics.setdefault("enchantment", {})
    enchantment.setdefault("active", None)
    enchantment.setdefault("last", None)
    return data


def save_session(player: str, data: dict) -> None:
    write_json(session_path(player), data)


def append_ledger(event: str, player: str, payload: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": now(), "event": event, "player": player, **payload}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def telegram_send(message: str, media: Path | None = None) -> bool:
    args = [
        "openclaw", "message", "send",
        "--target", "8729557865",
        "--channel", "telegram",
        "--account", "enchantify",
        message,
    ]
    if media:
        args += ["--media", str(media)]
    try:
        proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=60)
        return proc.returncode == 0
    except Exception:
        return False


def visual_prompt(spell: str, target: str, proof: str, outcome: str) -> str:
    style, _slug = VISUAL_ENCHANTMENTS[spell]
    return (
        f"{style}. Transform the player's real-world proof into the visual result of the Enchantment. "
        f"Subject/target: {target}. Proof details: {proof}. Story outcome: {outcome}. "
        "Keep the composition clear and inspectable, with no random extra characters unless the proof names them. "
        "No readable text except decorative marginalia when the style calls for it."
    )


def generate_visual_artifact(spell: str, target: str, proof: str, outcome: str, source_image: Path | None) -> dict:
    if spell not in VISUAL_ENCHANTMENTS:
        return {}
    _style, slug = VISUAL_ENCHANTMENTS[spell]
    prompt = visual_prompt(spell, target, proof, outcome)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_target = "".join(ch.lower() if ch.isalnum() else "-" for ch in target)[:36].strip("-") or "target"
    output = IMAGE_DIR / f"{stamp}-{slug}-{safe_target}.png"
    prompt_file = IMAGE_DIR / f"{stamp}-{slug}-{safe_target}.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt, encoding="utf-8")

    try:
        import drawthings_scene  # type: ignore

        if source_image and source_image.exists():
            ok, detail = drawthings_scene.generate_img2img(
                prompt,
                source_image,
                output,
                steps=8,
                cfg_scale=1.5,
                denoising_strength=0.72,
                timeout_seconds=300,
            )
        else:
            ok, detail = drawthings_scene.generate(
                prompt,
                output,
                steps=8,
                cfg_scale=1.2,
                timeout_seconds=300,
            )
    except Exception as exc:
        ok, detail = False, f"visual artifact generation failed: {exc}"

    return {
        "prompt": str(prompt_file),
        "image": str(output) if ok else None,
        "ok": ok,
        "detail": detail,
        "source_image": str(source_image) if source_image else None,
    }


def update_belief(player: str, delta: int, dry_run: bool) -> None:
    if dry_run:
        return
    subprocess.run(
        [sys.executable, str(BASE / "scripts" / "update-player.py"), player, "belief", f"{delta:+d}"],
        cwd=BASE,
        check=True,
    )


def known_enchantments(player: str) -> list[str]:
    return scene_known_enchantments(player)


def scene_known_enchantments(player: str) -> list[str]:
    text = (BASE / "players" / f"{player}.md").read_text(encoding="utf-8", errors="replace")
    names: list[str] = []
    in_flyleaf = False
    for line in text.splitlines():
        if line.startswith("## The Flyleaf"):
            in_flyleaf = True
            continue
        if in_flyleaf and line.startswith("## "):
            break
        if not in_flyleaf or not line.startswith("|") or "---" in line or "Enchantment" in line:
            continue
        cells = [cell.strip().strip("*") for cell in line.strip("|").split("|")]
        if cells and cells[0]:
            names.append(cells[0])
    return names


def validate_spell(player: str, spell: str) -> None:
    known = known_enchantments(player)
    if spell not in known:
        known_text = ", ".join(known[:12]) or "none found"
        raise SystemExit(f"Unknown or unavailable Enchantment for {player}: {spell}. Known: {known_text}")


def active_or_die(player: str) -> dict:
    data = load_session(player)
    active = data.get("mechanics", {}).get("enchantment", {}).get("active")
    if not active:
        raise SystemExit("No active Enchantment awaiting proof. Start one first.")
    return data


def cmd_status(args: argparse.Namespace) -> int:
    state = mechanics_state.get_mechanics_state(BASE, args.player)
    active = state.get("active_enchantment")
    print("ENCHANTMENT STATUS")
    if active:
        print(f"ACTIVE: {active.get('spell')} on {active.get('target')}")
        print(f"STARTED: {active.get('started_at')}")
        print(f"PROOF_REQUIRED: {active.get('proof_required')}")
    else:
        print("ACTIVE: none")
    last = state.get("enchantment", {}).get("last")
    if last:
        print(f"LAST: {last.get('spell')} on {last.get('target')} -> {last.get('outcome')}")
    return 0


def cmd_offer(args: argparse.Namespace) -> int:
    validate_spell(args.player, args.spell)
    mechanics_state.record_event(BASE, args.player, "offer-enchantment")
    data = load_session(args.player)
    data["mechanics"]["enchantment"]["offer"] = {
        "spell": args.spell,
        "target": args.target,
        "reason": args.reason,
        "offered_at": now(),
    }
    save_session(args.player, data)
    append_ledger("offer", args.player, data["mechanics"]["enchantment"]["offer"])
    print(f"ENCHANTMENT_OFFERED: {args.spell}")
    print(f"TARGET: {args.target}")
    print("NEXT: If the player chooses it, run start. Do not narrate completion yet.")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    validate_spell(args.player, args.spell)
    data = load_session(args.player)
    existing = data["mechanics"]["enchantment"].get("active")
    if existing and not args.force:
        raise SystemExit(f"Active Enchantment already awaiting proof: {existing.get('spell')} on {existing.get('target')}")

    active = {
        "spell": args.spell,
        "target": args.target,
        "mode": args.mode,
        "started_at": now(),
        "cost": BELIEF_COST,
        "proof_required": "photo" if args.mode == "photo" else "detailed real-world description",
        "status": "awaiting-proof",
    }
    if not args.dry_run:
        update_belief(args.player, -BELIEF_COST, dry_run=False)
        mechanics_state.record_event(BASE, args.player, "accept-enchantment")
        data = load_session(args.player)
        data["mechanics"]["enchantment"]["active"] = active
        save_session(args.player, data)
        append_ledger("start", args.player, active)

    print(f"ENCHANTMENT_STARTED: {args.spell}")
    print(f"TARGET: {args.target}")
    print(f"COST: -{BELIEF_COST} Belief")
    print(f"PROOF_REQUIRED: {active['proof_required']}")
    print("SCENE_INSTRUCTION: Narrate initiation only. Ask the player for the proof. Do not resolve the effect yet.")
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    data = active_or_die(args.player)
    active = data["mechanics"]["enchantment"]["active"]
    proof = (args.proof or "").strip()
    if len(proof) < 12 and not args.force:
        raise SystemExit("Proof is too thin. Require a photo description or vivid real-world detail before completion.")

    visual = {}
    source_image = args.proof_image if args.proof_image and args.proof_image.exists() else None
    if active.get("spell") in VISUAL_ENCHANTMENTS and not args.no_image and not args.dry_run:
        visual = generate_visual_artifact(active["spell"], active["target"], proof, args.outcome, source_image)

    completed = {
        **active,
        "completed_at": now(),
        "proof": proof,
        "outcome": args.outcome,
        "reward": BELIEF_REWARD,
        "status": "completed",
    }
    if visual:
        completed["visual_artifact"] = visual
    update_belief(args.player, BELIEF_REWARD, dry_run=args.dry_run)
    if not args.dry_run:
        mechanics_state.record_event(BASE, args.player, "complete-enchantment")
        data = load_session(args.player)
        data["mechanics"]["enchantment"]["active"] = None
        data["mechanics"]["enchantment"]["last"] = completed
        save_session(args.player, data)
        append_ledger("complete", args.player, completed)

    print(f"ENCHANTMENT_COMPLETED: {completed['spell']}")
    print(f"TARGET: {completed['target']}")
    print(f"REWARD: +{BELIEF_REWARD} Belief")
    print(f"OUTCOME: {args.outcome}")
    if visual:
        if visual.get("ok"):
            print(f"VISUAL_ARTIFACT: {visual.get('image')}")
            if args.send_image and visual.get("image"):
                sent = telegram_send(f"{completed['spell']} left an image in the margins.", Path(visual["image"]))
                print(f"VISUAL_TELEGRAM_SENT: {sent}")
        else:
            print(f"VISUAL_ARTIFACT_FAILED: {visual.get('detail')}")
    print("SCENE_INSTRUCTION: Now narrate the sensory effect and how the real proof changes the story.")
    return 0


def cmd_decline(args: argparse.Namespace) -> int:
    mechanics_state.record_event(BASE, args.player, "decline-enchantment")
    append_ledger("decline", args.player, {"reason": args.reason})
    print("ENCHANTMENT_DECLINED")
    print("SCENE_INSTRUCTION: Acknowledge gently. Do not punish unless repeated declines are active.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canonical Enchantify Enchantment ritual runner.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    status = sub.add_parser("status")
    status.add_argument("player", nargs="?", default="bj")
    status.set_defaults(func=cmd_status)

    offer = sub.add_parser("offer")
    offer.add_argument("player")
    offer.add_argument("--spell", required=True)
    offer.add_argument("--target", required=True)
    offer.add_argument("--reason", default="")
    offer.set_defaults(func=cmd_offer)

    start = sub.add_parser("start")
    start.add_argument("player")
    start.add_argument("--spell", required=True)
    start.add_argument("--target", required=True)
    start.add_argument("--mode", choices=["photo", "description"], default="photo")
    start.add_argument("--force", action="store_true")
    start.add_argument("--dry-run", action="store_true")
    start.set_defaults(func=cmd_start)

    complete = sub.add_parser("complete")
    complete.add_argument("player")
    complete.add_argument("--proof", required=True)
    complete.add_argument("--proof-image", type=Path)
    complete.add_argument("--outcome", required=True)
    complete.add_argument("--force", action="store_true")
    complete.add_argument("--dry-run", action="store_true")
    complete.add_argument("--no-image", action="store_true")
    complete.add_argument("--send-image", action="store_true")
    complete.set_defaults(func=cmd_complete)

    decline = sub.add_parser("decline")
    decline.add_argument("player")
    decline.add_argument("--reason", default="")
    decline.set_defaults(func=cmd_decline)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
