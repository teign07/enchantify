#!/usr/bin/env python3
"""
scene_conductor.py — orchestrate one Enchantify scene across multiple modalities.

This is the first elegant layer for immersive scene delivery:
- one ScenePacket in
- many adapters out

Current adapters:
- Telegram text
- Telegram multi-voice audio
- smart lights via scripts/lights.py
- image generation brief export
- music brief export
- Spotify mood handoff export

Design goals:
- one shared scene id
- explicit intensity mode
- graceful degradation
- dry-run first
- simple JSON packet shape that other scripts can emit later

Example:
  python3 scripts/scene_conductor.py --packet /tmp/scene.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

DEFAULT_ROUTING_MODEL = "openai-codex/gpt-5.4-mini"
ESSENTIAL = "essential"
ENRICHING = "enriching"
ORNAMENTAL = "ornamental"

BASE = Path(__file__).resolve().parent.parent
TMP = BASE / "tmp"
TEXT_OUTBOX = TMP / "scene-outbox"
ARTIFACT_OUTBOX = TEXT_OUTBOX / "artifacts"

INTENSITY_SEQUENCES = {
    "quiet": ["text", "voice"],
    "cinematic": ["text", "image", "voice"],
    "ritual": ["text", "image", "voice", "music", "spotify", "lights", "printer"],
}


def resolve_sequence(data: dict[str, Any]) -> list[str]:
    explicit = data.get("sequence")
    if explicit:
        return explicit

    intensity = data.get("intensity", "cinematic")
    channel = data.get("channel", "telegram")
    base = list(INTENSITY_SEQUENCES.get(intensity, INTENSITY_SEQUENCES["cinematic"]))

    # Telegram scene feel: text should open immediately, and if both image and
    # voice are present, voice should come right after image, while preserving
    # the rest of the sequence.
    if channel == "telegram" and data.get("image") and data.get("voice"):
        ordered = [step for step in base if step not in ("image", "voice")]
        insert_at = 1 if ordered and ordered[0] == "text" else 0
        ordered[insert_at:insert_at] = ["image", "voice"]
        return ordered

    return base


@dataclass
class CuePolicy:
    importance: str = ENRICHING
    fallback: str = "skip"
    cost_tier: str = "low"
    async_ok: bool = True


@dataclass
class VoiceTrack:
    text: str
    mode: str = "multi_voice_tts"
    policy: CuePolicy = field(default_factory=lambda: CuePolicy(importance=ESSENTIAL, fallback="text_only", cost_tier="low", async_ok=False))


@dataclass
class TextMessage:
    text: str
    reply_to: Optional[str] = None
    policy: CuePolicy = field(default_factory=lambda: CuePolicy(importance=ESSENTIAL, fallback="none", cost_tier="low", async_ok=False))


@dataclass
class LightCue:
    scene: Optional[str] = None
    color: Optional[str] = None
    brightness: Optional[int] = None
    transition: Optional[float] = None
    policy: CuePolicy = field(default_factory=lambda: CuePolicy(importance=ORNAMENTAL, fallback="no_op", cost_tier="low", async_ok=True))


@dataclass
class ImageCue:
    prompt: str
    filename_hint: Optional[str] = None
    size: str = "1216x832"
    style: str = "whimsical, dark, modern anime with pops of color"
    deliver: bool = True
    backend: str = "drawthings"
    policy: CuePolicy = field(default_factory=lambda: CuePolicy(importance=ENRICHING, fallback="skip_or_wallpaper", cost_tier="medium", async_ok=True))


@dataclass
class MusicCue:
    prompt: str
    instrumental: bool = True
    duration_seconds: int = 20
    model_hint: str = "meta music gen small"
    deliver: bool = False
    policy: CuePolicy = field(default_factory=lambda: CuePolicy(importance=ORNAMENTAL, fallback="spotify_then_silence", cost_tier="medium", async_ok=True))


@dataclass
class SpotifyCue:
    mood: str
    action: str = "mood_only"
    chapter: str = "Tidecrest"
    tier: str = "Influenced"
    policy: CuePolicy = field(default_factory=lambda: CuePolicy(importance=ORNAMENTAL, fallback="silence", cost_tier="low", async_ok=True))


@dataclass
class PrinterCue:
    artifact_type: str
    content: str
    filename_hint: Optional[str] = None
    printer: Optional[str] = None
    policy: CuePolicy = field(default_factory=lambda: CuePolicy(importance=ORNAMENTAL, fallback="queue_artifact", cost_tier="low", async_ok=True))


@dataclass
class ScenePacket:
    scene_id: str
    title: str
    mood: str
    intensity: str = "cinematic"  # quiet | cinematic | ritual
    target: Optional[str] = None
    channel: str = "telegram"
    account: str = "enchantify"
    routing_model: str = DEFAULT_ROUTING_MODEL
    sequence: list[str] = field(default_factory=lambda: ["text", "voice", "image", "lights", "music", "spotify", "printer"])
    text: Optional[TextMessage] = None
    voice: Optional[VoiceTrack] = None
    lights: Optional[LightCue] = None
    image: Optional[ImageCue] = None
    music: Optional[MusicCue] = None
    spotify: Optional[SpotifyCue] = None
    printer: Optional[PrinterCue] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenePacket":
        return cls(
            scene_id=data.get("scene_id") or f"scene-{uuid.uuid4().hex[:10]}",
            title=data["title"],
            mood=data["mood"],
            intensity=data.get("intensity", "cinematic"),
            target=data.get("target"),
            channel=data.get("channel", "telegram"),
            account=data.get("account", "enchantify"),
            routing_model=data.get("routing_model", DEFAULT_ROUTING_MODEL),
            sequence=resolve_sequence(data),
            text=_build_dataclass(TextMessage, data.get("text")),
            voice=_build_dataclass(VoiceTrack, data.get("voice")),
            lights=_build_dataclass(LightCue, data.get("lights")),
            image=_build_dataclass(ImageCue, data.get("image")),
            music=_build_dataclass(MusicCue, data.get("music")),
            spotify=_build_dataclass(SpotifyCue, data.get("spotify")),
            printer=_build_dataclass(PrinterCue, data.get("printer")),
            metadata=data.get("metadata", {}),
        )


def _build_dataclass(cls, payload: Optional[dict[str, Any]]):
    if not payload:
        return None
    payload = dict(payload)
    if "policy" in payload and isinstance(payload["policy"], dict):
        payload["policy"] = CuePolicy(**payload["policy"])
    return cls(**payload)


class Conductor:
    def __init__(self, packet: ScenePacket, dry_run: bool = False):
        self.packet = packet
        self.dry_run = dry_run
        self.buffered_delivery = packet.channel == "telegram"
        self.pending_deliveries: dict[str, dict[str, Any]] = {}
        TEXT_OUTBOX.mkdir(parents=True, exist_ok=True)
        ARTIFACT_OUTBOX.mkdir(parents=True, exist_ok=True)

    def _run(self, args: list[str], timeout: int = 90) -> tuple[bool, str]:
        if self.dry_run:
            return True, f"DRY RUN: {' '.join(args)}"
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            out = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode == 0, out.strip()
        except subprocess.TimeoutExpired:
            return False, f"timed out after {timeout}s: {' '.join(args)}"

    def _policy_summary(self, cue: Any) -> dict[str, Any]:
        policy = getattr(cue, "policy", None)
        if not policy:
            return {}
        return asdict(policy)

    def _extract_message_ids(self, text: str) -> list[str]:
        return re.findall(r"Message ID:\s*(\d+)", text or "")

    def _extract_path(self, text: str) -> Optional[str]:
        m = re.search(r"(/[^\s|]+)", text or "")
        return m.group(1) if m else None

    def _extract_media_path(self, text: str) -> Optional[str]:
        m = re.search(r"^MEDIA:\s*(.+)$", text or "", re.MULTILINE)
        return m.group(1).strip() if m else None

    def _send_text_message(self, text: str) -> tuple[bool, str]:
        if not self.packet.target:
            return True, "no target for text send"
        args = [
            "openclaw",
            "message",
            "send",
            "--target",
            self.packet.target,
            "--channel",
            self.packet.channel,
        ]
        if self.packet.account:
            args += ["--account", self.packet.account]
        args += ["--message", text]
        return self._run(args, timeout=60)

    def _send_media(self, media_path: str) -> tuple[bool, str]:
        if not self.packet.target:
            return True, "no target for media send"
        args = [
            "openclaw",
            "message",
            "send",
            "--target",
            self.packet.target,
            "--channel",
            self.packet.channel,
        ]
        if self.packet.account:
            args += ["--account", self.packet.account]
        args += ["--media", media_path]
        return self._run(args, timeout=120)

    def _normalize_result(self, step: str, ok: bool, detail: str) -> dict[str, Any]:
        raw = detail or ""
        result: dict[str, Any] = {
            "ok": ok,
            "detail": raw,
            "summary": raw.splitlines()[0][:240] if raw else ("ok" if ok else "failed"),
        }

        if "timed out after" in raw:
            result["timed_out"] = True

        msg_ids = self._extract_message_ids(raw)
        if msg_ids:
            result["message_ids"] = msg_ids

        if step == "text" and ok and self.packet.target:
            result["summary"] = "text sent"
        elif step == "voice" and ok:
            result["summary"] = "voice sent" if msg_ids else "voice completed"
        elif step == "image" and ok:
            if "sent from" in raw:
                result["summary"] = "image generated and sent"
            elif "generated at" in raw:
                result["summary"] = "image generated"
            elif "brief written" in raw:
                result["summary"] = "image brief written"
            path = self._extract_path(raw)
            if path:
                result["artifact_path"] = path
        elif step == "printer" and ok:
            result["summary"] = "printer artifact queued"
            path = self._extract_path(raw)
            if path:
                result["artifact_path"] = path
        elif step in ("music", "spotify") and ok:
            result["summary"] = f"{step} brief written"

        return result

    def deliver_text(self) -> tuple[bool, str]:
        if not self.packet.text:
            return True, "no text cue"

        payload = {
            "scene_id": self.packet.scene_id,
            "channel": self.packet.channel,
            "target": self.packet.target,
            "account": self.packet.account,
            "reply_to": self.packet.text.reply_to,
            "text": self.packet.text.text,
            "routing_model": self.packet.routing_model,
            "policy": self._policy_summary(self.packet.text),
            "created_at": datetime.now().isoformat(),
        }
        out = TEXT_OUTBOX / f"{self.packet.scene_id}-text.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        if not self.packet.target:
            return True, f"text payload written to {out}"

        if self.buffered_delivery:
            self.pending_deliveries["text"] = {"text": self.packet.text.text}
            return True, f"text prepared and payload written to {out}"

        ok, detail = self._send_text_message(self.packet.text.text)
        if ok:
            return True, f"text sent and payload written to {out}"
        return False, f"text send failed | payload written to {out} | {detail}"

    def deliver_voice(self) -> tuple[bool, str]:
        if not self.packet.voice or not self.packet.target:
            return True, "no voice cue"
        args = [
            sys.executable,
            str(BASE / "scripts" / "multi_voice_tts.py"),
        ]
        if not self.buffered_delivery:
            args += [
                "--target", self.packet.target,
                "--channel", self.packet.channel,
                "--account", self.packet.account,
                "--audio-only",
            ]
        args += [self.packet.voice.text]
        ok, detail = self._run(args, timeout=240)
        if not ok:
            return ok, detail
        if self.buffered_delivery:
            if self.dry_run:
                media_path = str(TEXT_OUTBOX / f"{self.packet.scene_id}-voice.ogg")
                self.pending_deliveries["voice"] = {"media_path": media_path}
                return True, f"voice prepared at {media_path}"
            media_path = self._extract_media_path(detail)
            if not media_path:
                return False, f"voice generated but media path missing | {detail}"
            self.pending_deliveries["voice"] = {"media_path": media_path}
            return True, f"voice generated at {media_path}"
        return ok, detail

    def deliver_lights(self) -> tuple[bool, str]:
        if not self.packet.lights:
            return True, "no light cue"
        if self.packet.lights.scene:
            args = [sys.executable, str(BASE / "scripts" / "lights.py"), "scene", self.packet.lights.scene]
            return self._run(args, timeout=30)
        if self.packet.lights.color:
            args = [sys.executable, str(BASE / "scripts" / "lights.py"), "set", "--color", self.packet.lights.color]
            if self.packet.lights.brightness is not None:
                args += ["--bright", str(self.packet.lights.brightness)]
            if self.packet.lights.transition is not None:
                args += ["--transition", str(self.packet.lights.transition)]
            return self._run(args, timeout=30)
        return True, "light cue had no actionable fields"

    def export_image_brief(self) -> tuple[bool, str]:
        if not self.packet.image:
            return True, "no image cue"
        payload = asdict(self.packet.image) | {
            "scene_id": self.packet.scene_id,
            "routing_model": self.packet.routing_model,
        }
        out = TEXT_OUTBOX / f"{self.packet.scene_id}-image.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        if self.packet.image.backend != "drawthings":
            return True, f"image brief written to {out}"

        prompt_file = TEXT_OUTBOX / f"{self.packet.scene_id}-drawthings-prompt.txt"
        prompt_file.write_text(self.packet.image.prompt, encoding="utf-8")

        image_path = TEXT_OUTBOX / (self.packet.image.filename_hint or f"{self.packet.scene_id}.png")
        args = [
            sys.executable,
            str(BASE / "scripts" / "drawthings_scene.py"),
            "--prompt-file",
            str(prompt_file),
            "--output",
            str(image_path),
        ]
        ok, detail = self._run(args, timeout=300)
        if not ok:
            return True, f"drawthings unavailable, image brief written to {out} | fallback: {detail}"

        if self.buffered_delivery and self.packet.image.deliver and self.packet.target:
            self.pending_deliveries["image"] = {"media_path": str(image_path)}
            return True, f"drawthings image generated at {image_path} | brief written to {out}"

        if self.packet.image.deliver and self.packet.target:
            send_args = [
                "openclaw",
                "message",
                "send",
                "--target",
                self.packet.target,
                "--channel",
                self.packet.channel,
            ]
            if self.packet.account:
                send_args += ["--account", self.packet.account]
            send_args += ["--media", str(image_path)]
            send_ok, send_detail = self._run(send_args, timeout=120)
            if send_ok:
                return True, f"drawthings image generated and sent from {image_path} | brief written to {out}"
            return False, f"image generated at {image_path} but send failed | brief written to {out} | {send_detail}"

        return True, f"drawthings image generated at {image_path} | brief written to {out}"

    def export_music_brief(self) -> tuple[bool, str]:
        if not self.packet.music:
            return True, "no music cue"
        out = TEXT_OUTBOX / f"{self.packet.scene_id}-music.json"
        out.write_text(json.dumps(asdict(self.packet.music) | {"scene_id": self.packet.scene_id, "routing_model": self.packet.routing_model}, indent=2), encoding="utf-8")

        prompt_file = TEXT_OUTBOX / f"{self.packet.scene_id}-music-prompt.txt"
        prompt_file.write_text(self.packet.music.prompt, encoding="utf-8")
        audio_path = TEXT_OUTBOX / f"{self.packet.scene_id}-music.wav"
        args = [
            sys.executable,
            str(BASE / "scripts" / "musicgen_scene.py"),
            "--prompt-file",
            str(prompt_file),
            "--output",
            str(audio_path),
            "--duration",
            str(self.packet.music.duration_seconds),
        ]
        ok, detail = self._run(args, timeout=420)
        if not ok:
            return False, f"music generation failed | brief written to {out} | {detail}"

        if self.packet.music.deliver and self.packet.target:
            send_args = [
                "openclaw",
                "message",
                "send",
                "--target",
                self.packet.target,
                "--channel",
                self.packet.channel,
            ]
            if self.packet.account:
                send_args += ["--account", self.packet.account]
            send_args += ["--media", str(audio_path)]
            send_ok, send_detail = self._run(send_args, timeout=120)
            if send_ok:
                return True, f"music generated and sent from {audio_path} | brief written to {out}"
            return False, f"music generated at {audio_path} but send failed | brief written to {out} | {send_detail}"

        return True, f"music generated at {audio_path} | brief written to {out}"

    def export_spotify_brief(self) -> tuple[bool, str]:
        if not self.packet.spotify:
            return True, "no spotify cue"
        out = TEXT_OUTBOX / f"{self.packet.scene_id}-spotify.json"
        out.write_text(json.dumps(asdict(self.packet.spotify) | {"scene_id": self.packet.scene_id, "routing_model": self.packet.routing_model}, indent=2), encoding="utf-8")

        driver_script = (
            "from pathlib import Path\n"
            "import importlib.util, sys\n"
            f"base_dir = Path({str(BASE)!r})\n"
            "driver_path = base_dir / 'scripts' / 'pact-drivers' / 'spotify.py'\n"
            "base_path = base_dir / 'scripts' / 'pact-drivers' / 'base.py'\n"
            "base_spec = importlib.util.spec_from_file_location('pact_drivers.base', base_path)\n"
            "base_mod = importlib.util.module_from_spec(base_spec)\n"
            "sys.modules['pact_drivers.base'] = base_mod\n"
            "base_spec.loader.exec_module(base_mod)\n"
            "spec = importlib.util.spec_from_file_location('pact_drivers.spotify', driver_path)\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['pact_drivers.spotify'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            f"print(mod.SpotifyDriver().execute({self.packet.spotify.tier!r}, {self.packet.spotify.chapter!r}, {{'mood': {self.packet.spotify.mood!r}, 'action': {self.packet.spotify.action!r}}}, dry_run={self.dry_run!r}))\n"
        )
        ok, detail = self._run([sys.executable, "-c", driver_script], timeout=30)
        if ok:
            return True, f"spotify acted | brief written to {out} | {detail}"
        return False, f"spotify action failed | brief written to {out} | {detail}"

    def export_printer_brief(self) -> tuple[bool, str]:
        if not self.packet.printer:
            return True, "no printer cue"
        artifact = asdict(self.packet.printer) | {
            "scene_id": self.packet.scene_id,
            "title": self.packet.title,
            "routing_model": self.packet.routing_model,
            "queued_at": datetime.now().isoformat(),
        }
        out = ARTIFACT_OUTBOX / f"{self.packet.scene_id}-print.json"
        out.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return True, f"printer artifact queued at {out}"

    def _handlers(self) -> dict[str, Callable[[], tuple[bool, str]]]:
        return {
            "text": self.deliver_text,
            "voice": self.deliver_voice,
            "image": self.export_image_brief,
            "lights": self.deliver_lights,
            "music": self.export_music_brief,
            "spotify": self.export_spotify_brief,
            "printer": self.export_printer_brief,
        }

    def _write_run_record(self, results: dict[str, dict[str, Any]]) -> None:
        out = TEXT_OUTBOX / f"{self.packet.scene_id}-run.json"
        essential_steps = [step for step in self.packet.sequence if step in ("text", "voice")]
        essential_ok = all(results.get(step, {}).get("ok") for step in essential_steps)
        delivery_ok = all(item.get("ok") for item in results.values())
        payload = {
            "scene_id": self.packet.scene_id,
            "title": self.packet.title,
            "sequence": self.packet.sequence,
            "routing_model": self.packet.routing_model,
            "dry_run": self.dry_run,
            "ran_at": datetime.now().isoformat(),
            "essential_steps": essential_steps,
            "essential_ok": essential_ok,
            "delivery_ok": delivery_ok,
            "results": results,
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _flush_pending_deliveries(self, results: dict[str, dict[str, Any]]) -> None:
        for step in self.packet.sequence:
            pending = self.pending_deliveries.get(step)
            if not pending:
                continue
            send_started = datetime.now().isoformat()
            if step == "text":
                ok, detail = self._send_text_message(pending["text"])
                summary = "text sent"
            else:
                ok, detail = self._send_media(pending["media_path"])
                summary = f"{step} sent"
            send_finished = datetime.now().isoformat()
            current = results.setdefault(step, {})
            current["delivered"] = ok
            current["delivery_detail"] = detail
            current["delivery_started_at"] = send_started
            current["delivery_finished_at"] = send_finished
            if ok:
                current["summary"] = summary
                msg_ids = self._extract_message_ids(detail)
                if msg_ids:
                    current["message_ids"] = msg_ids
            else:
                current["ok"] = False
                current["summary"] = f"{step} delivery failed"

    def run(self) -> dict[str, dict[str, Any]]:
        handlers = self._handlers()
        results: dict[str, dict[str, Any]] = {}
        for step in self.packet.sequence:
            handler = handlers.get(step)
            if not handler:
                results[step] = {
                    "ok": False,
                    "detail": f"unknown step: {step}",
                    "started_at": datetime.now().isoformat(),
                    "finished_at": datetime.now().isoformat(),
                }
                continue
            started_at = datetime.now().isoformat()
            ok, detail = handler()
            finished_at = datetime.now().isoformat()
            results[step] = self._normalize_result(step, ok, detail)
            results[step]["started_at"] = started_at
            results[step]["finished_at"] = finished_at
        if self.buffered_delivery:
            self._flush_pending_deliveries(results)
        self._write_run_record(results)
        return results


def load_packet(path: Path) -> ScenePacket:
    data = json.loads(path.read_text(encoding="utf-8"))
    return ScenePacket.from_dict(data)


def example_packet() -> dict[str, Any]:
    return {
        "scene_id": "scene-wicker-corridor-demo",
        "title": "Wicker in the corridor",
        "mood": "tense invitation",
        "intensity": "cinematic",
        "channel": "telegram",
        "account": "enchantify",
        "routing_model": "openai-codex/gpt-5.4-mini",
        "target": "8729557865",
        "text": {
            "text": "You turn into the corridor and the lamps burn a little too gold. Wicker Eddies is waiting."
        },
        "voice": {
            "text": "[bm_lewis] You turn into the corridor and the lamps burn a little too gold. [am_liam] You do have a talent for arriving exactly when things get interesting."
        },
        "lights": {
            "scene": "tension"
        },
        "image": {
            "prompt": "Wicker Eddies in a haunted library corridor, warm lampglow against deep shadow, whimsical dark modern anime with pops of color",
            "filename_hint": "wicker-corridor.png",
            "backend": "drawthings"
        },
        "music": {
            "prompt": "tense magical corridor cue, subtle pulse, paper and ink atmosphere, unresolved but inviting",
            "instrumental": True,
            "duration_seconds": 20,
            "deliver": False
        },
        "spotify": {
            "mood": "dark academic tension with a pulse of invitation"
        },
        "printer": {
            "artifact_type": "scene-card",
            "content": "Wicker Eddies. Corridor. A wrong door appears where no door should be.",
            "filename_hint": "wicker-corridor-scene-card.txt",
            "policy": {
                "importance": "ornamental",
                "fallback": "queue_artifact",
                "cost_tier": "low",
                "async_ok": True
            }
        },
        "metadata": {
            "location": "library corridor",
            "speaker": ["Wicker Eddies"],
            "preserve_scene_construction": True,
            "source_systems": ["session-entry", "scene-director", "narrative-weight"]
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, help="Path to ScenePacket JSON")
    parser.add_argument("--emit-example", action="store_true", help="Print example ScenePacket JSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.emit_example:
        print(json.dumps(example_packet(), indent=2))
        return 0

    if not args.packet:
        print("Pass --packet /path/to/scene.json or use --emit-example", file=sys.stderr)
        return 1

    packet = load_packet(args.packet)
    results = Conductor(packet, dry_run=args.dry_run).run()
    essential_steps = [step for step in packet.sequence if step in ("text", "voice")]
    essential_ok = all(results.get(step, {}).get("ok") for step in essential_steps)
    delivery_ok = all(item.get("ok") for item in results.values())
    print(json.dumps({
        "scene_id": packet.scene_id,
        "sequence": packet.sequence,
        "essential_steps": essential_steps,
        "essential_ok": essential_ok,
        "delivery_ok": delivery_ok,
        "results": results,
    }, indent=2))
    return 0 if essential_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
