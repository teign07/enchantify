---
name: drawthings
description: Generate images through the local Draw Things HTTP API on this Mac. Use when the user wants local image generation instead of the built-in image_generate tool, especially when the working wallpaper.py-style local Draw Things path is desired.
---

# Draw Things Image Generator

When the user asks for local image generation through Draw Things, run:
`bash /Users/bj/.openclaw/workspace/enchantify/skills/drawthings/generate.sh "YOUR PROMPT HERE"`

Rules:
- This skill uses the local Draw Things API at `http://127.0.0.1:8080/sdapi/v1/txt2img`
- If the script returns `MEDIA:<path>`, reply with that exact line
- If the script returns an `ERROR:` line saying the API is unreachable, tell the user Draw Things is not open or HTTP API is not enabled
- Do not use the built-in image_generate tool when the user specifically wants the local Draw Things path
