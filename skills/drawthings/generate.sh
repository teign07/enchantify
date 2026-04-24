#!/bin/bash

python3 - "$1" << 'EOF'
import sys, json, urllib.request, urllib.error, os, time, base64

prompt = sys.argv[1]
url = "http://127.0.0.1:8080/sdapi/v1/txt2img"

payload = {
    "prompt": prompt,
    "negative_prompt": "",
    "width": 1024,
    "height": 1024,
    "steps": 4,
    "cfg_scale": 1.0,
    "seed": -1,
}

req = urllib.request.Request(
    url,
    json.dumps(payload).encode("utf-8"),
    {"Content-Type": "application/json"},
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        images = res.get("images") or []
        if not images:
            print("ERROR: Draw Things returned no images")
            raise SystemExit(1)

        b64 = images[0]
        if "," in b64:
            b64 = b64.split(",", 1)[1]

        out_dir = os.path.expanduser("~/.openclaw/media")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"drawthings_{int(time.time())}.png")

        with open(out_file, "wb") as f:
            f.write(base64.b64decode(b64))

        print(f"MEDIA:{out_file}")

except urllib.error.URLError as e:
    print(f"ERROR: Draw Things API unreachable at {url}. Is the app open and HTTP API enabled? {e}")
except urllib.error.HTTPError as e:
    error_info = e.read().decode("utf-8", errors="ignore")
    print(f"ERROR: Draw Things rejected the request (HTTP {e.code}): {error_info}")
except Exception as e:
    print(f"ERROR: Failed to connect or save image: {e}")
EOF
