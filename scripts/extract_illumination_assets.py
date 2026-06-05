#!/usr/bin/env python3
"""Extract green-screen marginalia sheets into app asset catalog imagesets."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


SOURCES = [
    Path("/private/var/folders/d4/3gn8vlsx07z5779_6_nqh8ww0000gn/T/TemporaryItems/com.apple.Photos.NSItemProvider/uuid=B1F018A4-5821-411D-AEA7-0888A0ABDD70&code=001&library=1&type=1&mode=1&loc=true&cap=true.jpeg/Image.jpeg"),
    Path("/private/var/folders/d4/3gn8vlsx07z5779_6_nqh8ww0000gn/T/TemporaryItems/com.apple.Photos.NSItemProvider/uuid=4A1D4FA3-C017-4BBA-B4BF-1A8CCC9E0EB4&code=001&library=1&type=1&mode=1&loc=true&cap=true.jpeg/Image 2.jpeg"),
    Path("/private/var/folders/d4/3gn8vlsx07z5779_6_nqh8ww0000gn/T/TemporaryItems/com.apple.Photos.NSItemProvider/uuid=606DF8D3-DA09-4892-B9BB-211E38E20B1E&code=001&library=1&type=1&mode=1&loc=true&cap=true.jpeg/Image 3.jpeg"),
]


ASSET_ROOT = Path("ios/InsideCover/InsideCoverApp/Assets.xcassets")


def is_green_screen(rgb: np.ndarray) -> np.ndarray:
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    return (g > 115) & (g > r * 13 // 8) & (g > b * 13 // 8)


def components(mask: np.ndarray):
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    for y in range(height):
        xs = np.flatnonzero(mask[y] & ~seen[y])
        for x0 in xs:
            if seen[y, x0] or not mask[y, x0]:
                continue
            q = deque([(x0, y)])
            seen[y, x0] = True
            min_x = max_x = x0
            min_y = max_y = y
            count = 0
            while q:
                x, yy = q.pop()
                count += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, yy)
                max_y = max(max_y, yy)
                for nx, ny in ((x + 1, yy), (x - 1, yy), (x, yy + 1), (x, yy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            yield (min_x, min_y, max_x + 1, max_y + 1, count)


def write_imageset(name: str, image: Image.Image) -> None:
    directory = ASSET_ROOT / f"{name}.imageset"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{name}.png"
    image.save(directory / filename)
    contents = {
        "images": [
            {
                "filename": filename,
                "idiom": "universal",
                "scale": "1x",
            }
        ],
        "info": {
            "author": "xcode",
            "version": 1,
        },
        "properties": {
            "preserves-vector-representation": False,
        },
    }
    (directory / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n")


def main() -> None:
    exported = []
    for sheet_index, path in enumerate(SOURCES, start=1):
        if not path.exists():
            raise SystemExit(f"Missing source sheet: {path}")
        source = Image.open(path).convert("RGBA")
        rgba = np.asarray(source)
        green = is_green_screen(rgba[:, :, :3])
        object_mask = ~green

        found = []
        for box in components(object_mask):
            min_x, min_y, max_x, max_y, count = box
            width = max_x - min_x
            height = max_y - min_y
            if count < 1300 or width < 26 or height < 26:
                continue
            if width > source.width * 0.86 and height > source.height * 0.86:
                continue
            found.append(box)

        found.sort(key=lambda item: item[4], reverse=True)
        for asset_index, (min_x, min_y, max_x, max_y, _count) in enumerate(found[:28], start=1):
            pad = 8
            min_x = max(0, min_x - pad)
            min_y = max(0, min_y - pad)
            max_x = min(source.width, max_x + pad)
            max_y = min(source.height, max_y + pad)
            crop = rgba[min_y:max_y, min_x:max_x].copy()
            crop_green = is_green_screen(crop[:, :, :3])
            alpha = np.where(crop_green, 0, crop[:, :, 3])
            crop[:, :, 3] = alpha.astype(np.uint8)
            image = Image.fromarray(crop, mode="RGBA")
            name = f"IlluminationScrapS{sheet_index:02d}_{asset_index:02d}"
            write_imageset(name, image)
            exported.append(name)

    print("\n".join(exported))


if __name__ == "__main__":
    main()
