#!/usr/bin/env python3
"""
musicgen_scene.py — generate a short scene cue with Meta MusicGen Small.

Usage:
  python3 scripts/musicgen_scene.py --prompt-file /tmp/prompt.txt --output /tmp/scene.wav
  python3 scripts/musicgen_scene.py --prompt "tense magical corridor cue" --duration 20 --output /tmp/scene.wav
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

MODEL_ID = "facebook/musicgen-small"
_DEFAULT_SR = 32000


def read_prompt(prompt: str | None, prompt_file: Path | None) -> str:
    if prompt_file and prompt_file.exists():
        text = prompt_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    return (prompt or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=20)
    args = parser.parse_args()

    prompt = read_prompt(args.prompt, args.prompt_file)
    if not prompt:
        raise SystemExit("missing prompt")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = MusicgenForConditionalGeneration.from_pretrained(MODEL_ID)
    model.to(device)

    inputs = processor(
        text=[prompt],
        padding=True,
        return_tensors="pt",
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    max_new_tokens = max(1, int(args.duration * 50))
    audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    sample_rate = getattr(model.config.audio_encoder, "sampling_rate", _DEFAULT_SR)
    audio = audio_values[0, 0].detach().cpu()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        import soundfile as sf
        sf.write(str(args.output), audio.numpy(), sample_rate)
    except Exception:
        import wave
        import array
        clipped = torch.clamp(audio, -1.0, 1.0)
        pcm = array.array("h", (int(x * 32767) for x in clipped.tolist()))
        with wave.open(str(args.output), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())

    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
