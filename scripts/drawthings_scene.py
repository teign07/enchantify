#!/usr/bin/env python3
"""
drawthings_scene.py — generate a scene image via local Draw Things API.

Usage:
  python3 scripts/drawthings_scene.py --prompt-file /tmp/prompt.txt --output /tmp/out.png
  python3 scripts/drawthings_scene.py --prompt "haunted library corridor" --output /tmp/out.png
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from urllib import error, request


def generate(prompt: str, output: Path, width: int = 1280, height: int = 720, steps: int = 4, cfg_scale: float = 1.0, timeout_seconds: int = 300) -> tuple[bool, str]:
    url = "http://127.0.0.1:8080/sdapi/v1/txt2img"
    payload = {
        "prompt": prompt,
        "negative_prompt": "",
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "seed": -1,
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
        images = result.get("images") or []
        if not images:
            return False, "no image data returned from Draw Things"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(images[0]))
        return True, str(output)
    except error.URLError as e:
        return False, f"Draw Things unavailable: {e}"
    except Exception as e:
        return False, f"Draw Things error: {e}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--cfg-scale", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    prompt = args.prompt
    if not prompt and args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    if not prompt:
        raise SystemExit("Provide --prompt or --prompt-file")

    ok, detail = generate(prompt, args.output, width=args.width, height=args.height, steps=args.steps, cfg_scale=args.cfg_scale, timeout_seconds=args.timeout_seconds)
    print(detail)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
