# Cinematic Story-Field Journal

Player-facing **game interface** — separate from Mission Control (`mission-control.py` on port 9191).

## Run

```bash
cd /Users/bj/.openclaw/workspace/enchantify
python3 scripts/story-field-journal.py --serve --open
```

- **Field Graph (3D explorer):** http://127.0.0.1:9192/field
- **Folio UI (tabs):** http://127.0.0.1:9192/
- **Graph API:** http://127.0.0.1:9192/api/graph?player=bj
- **Folio API:** http://127.0.0.1:9192/api/folio?player=bj
- **Ops desk (unchanged):** http://127.0.0.1:9191/hooks/mission-control.html

Build graph JSON only: `python3 scripts/field-graph.py bj`

## Tabs

Today · Compass · Enchantments · Library · Desk — same spine as `mobile-gateway.py`.

Play still happens in **Telegram**; this folio reads live state (page contract, scene outbox, threads, Inside Cover).

## Merge later

Data layer is shared (`mobile-gateway` packet + world-register threads). Presentation is isolated under `hooks/story-field-journal/` for cinematic iteration without touching the 22-tab ops folio.
