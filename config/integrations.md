# Enchantify Integrations

*Enabled features for this installation. The Labyrinth reads this at session start and only uses integrations marked as enabled.*

---

## Status

|Integration |Enabled |Config |
|------------|--------|-------|
|Spotify (Music) |✅ Yes |AppleScript (local) |
|Smart Lights |✅ Yes |LIFX LAN (local) |
|Image Generation |⏳ Yes | openai dall-e 3 |
|Printer |⏳ Yes | TOOLS.md (local) |
|Weather/Tides/Moon |✅ Yes |Silvie's HEARTBEAT.md symlink |
|Calendar |⏳ Yes instructions in TOOLS.md |

---

## Spotify (Music) — ENABLED

**Connection:** AppleScript (local macOS control)
**Account:** bj's personal Spotify
**Tested:** ✅ March 22, 2026

### Available Commands

```applescript
-- Play/pause toggle
tell application "Spotify" to playpause

-- Play (if paused)
tell application "Spotify" to play

-- Pause
tell application "Spotify" to pause

-- Set volume (0-100)
tell application "Spotify" to set sound volume to 50

-- Get current volume
tell application "Spotify" to get sound volume

-- Get current track name
tell application "Spotify" to get name of current track

-- Get current artist
tell application "Spotify" to get artist of current track

-- Get player state (playing/paused/stopped)
tell application "Spotify" to get player state

-- Play playlist by name
tell application "Spotify" to play playlist "Playlist Name"
```

### Music Scripts (from AGENTS.md)

|Narrative Moment |Music Direction |Volume |
|-----------------|----------------|-------|
|Academy exploration |Whimsical, light orchestral (Ghibli-adjacent) |40-50 |
|Classroom scenes |Quiet, studious ambient |30-40 |
|The Nothing approaches |Fade to silence, then low drone |10 → 0 |
|Combat / tension |Driving, percussive |50-60 |
|Compass Run — Notice (North) |Ambient curiosity, open, exploratory |35-45 |
|Compass Run — Embark (East) |Walking tempo, gentle momentum |40-50 |
|Compass Run — Sense (South) |Meditative, minimal, present |25-35 |
|Compass Run — Write (West) |**Silence. Complete silence.** |0 |
|Compass Run — Complete |Gentle resolution, warmth, return |35-45 |
|Book Jump — entering |Music shifts to match book's mood |45-55 |
|Book Jump — The Snow Queen |Ice white, cool blue |40 |
|Book Jump — The Odyssey |Warm Mediterranean gold |45 |
|Bookend (twilight town) |Melancholy, nostalgic, twilight |35-40 |

### Implementation Notes

- **Genre-based requests:** The Labyrinth can suggest genres ("whimsical orchestral," "dark ambient drone") and bj can queue playlists manually, OR we can implement Spotify API OAuth for programmatic playlist selection
- **Fade transitions:** Volume changes should happen gradually over 2-3 seconds for smooth transitions (multiple AppleScript calls with small delays)
- **Silence is a valid choice:** For the Write step, explicitly pause music — don't just lower volume
- **If Spotify is not running:** The Labyrinth should suggest music instead of failing: *"Put on something that sounds like a library at midnight."*

### Test Results (March 22, 2026)

```
✅ Play/pause: Working
✅ Volume control: Working (tested 10, 30, 50)
✅ Track metadata: Working ("The Last Unicorn" by America)
✅ Player state: Working (playing/paused detection)
```

---

## Smart Lights — ENABLED ✅

**System:** LIFX (LAN protocol via `lifxlan` library, no cloud)
**Bulbs:**
- Silvie Lamp (192.168.1.244)
- Silvie Aura (192.168.1.5)
**Control Script:** `scripts/lifx-control.py`
**Dependency:** `pip3 install lifxlan`
**Status:** ✅ Tested March 22, 2026

### Available Commands

```bash
# List all bulbs
python3 scripts/lifx-control.py list

# Power
python3 scripts/lifx-control.py power on
python3 scripts/lifx-control.py power off

# Custom color (hue, saturation, brightness, kelvin)
python3 scripts/lifx-control.py color 40000 15000 40000 3000

# Scenes (predefined)
python3 scripts/lifx-control.py scene academy
python3 scripts/lifx-control.py scene library
python3 scripts/lifx-control.py scene nothing
python3 scripts/lifx-control.py scene compass-north
python3 scripts/lifx-control.py scene compass-east
python3 scripts/lifx-control.py scene compass-south
python3 scripts/lifx-control.py scene compass-west
python3 scripts/lifx-control.py scene compass-complete
python3 scripts/lifx-control.py scene book-snow-queen
python3 scripts/lifx-control.py scene book-odyssey
python3 scripts/lifx-control.py scene bookend
python3 scripts/lifx-control.py scene defeated
```

**All commands control both bulbs simultaneously.**

### Scene Definitions

|Scene |Hue |Sat |Bright |Kelvin |Use |
|------|-----|-----|-------|-------|-----|
|academy |40000 |15000 |40000 |3000 |Warm amber, comfortable |
|library |50000 |20000 |35000 |4000 |Soft blue-purple |
|nothing |45000 |5000 |15000 |6500 |Cold, dim, unsettling |
|compass-north |0 |0 |50000 |3500 |Warm white, bright |
|compass-east |0 |0 |60000 |4500 |Daylight mode |
|compass-south |30000 |10000 |30000 |2700 |Soft warm meditative |
|compass-west |0 |0 |20000 |2700 |Single warm, dim |
|compass-complete |8000 |20000 |55000 |3000 |Golden sunrise |
|book-snow-queen |52000 |15000 |40000 |6500 |Ice white, cool |
|book-odyssey |10000 |15000 |45000 |3200 |Warm Mediterranean |
|bookend |55000 |25000 |35000 |3000 |Purple-pink sunset |
|defeated |10000 |20000 |60000 |3000 |Warm burst |

### Test Results (March 22, 2026)

```
✅ Power on: Working
✅ Scene academy: Working (warm amber)
✅ Scene nothing: Working (cold, dim)
✅ Scene compass-complete: Working (golden)
```

### Integration Notes

- **Duration:** All scene transitions use 1000ms (1 second) fade
- **No cloud dependency:** Works entirely over local LAN
- **If bulb is unreachable:** The Labyrinth should continue without lights — narrative doesn't block on lighting
- **Multiple bulbs:** To add more bulbs, duplicate the script with different IPs or extend to broadcast to all discovered bulbs

---

## Image Generation — DISABLED

**System:** Not configured
**Status:** Not needed for initial playtest

### When to Enable

- Character portrait at creation
- Scene illustrations at major transitions
- Book Jump arrivals
- Compass Run Sense step reimagining
- Souvenir card art

### Options

**Cloud (OpenAI DALL-E 3 / gpt-image-1):**
- Requires OpenAI API key
- ~$0.02-0.08 per image
- High quality, fast

**Local (Nano Banana / Stable Diffusion / Flux):**
- Free after setup
- Requires Apple Silicon M1+ with 16GB+ RAM or NVIDIA GPU
- 10-30 seconds per image

---

## Printer — ENABLED ✅

**Status:** Configured — March 30, 2026
**Primary:** `Silvie_s_Printer` (LAN)
**Backup:** `Canon_MG3600_series_backup`
**Script:** `scripts/print-souvenir.sh`

### When to Enable

After Compass Run completion — generates souvenir card with:
- Date, weather, season, moon
- The One-Sentence Souvenir
- Chapter affiliation
- Belief earned

### Modes

- **Auto-print:** Souvenir prints automatically
- **PDF save:** Saved to designated folder, player prints when ready
- **Off:** Digital only

---

## Weather / Tides / Moon / Full Heartbeat — VIA HEARTBEAT

**Source:** Symlink to Silvie's HEARTBEAT.md
**Path:** `config/player-heartbeat.md` → `~/.openclaw/workspace/HEARTBEAT.md`
**Status:** ✅ Active — Full bleed enabled March 29, 2026

### Available Data

- Weather (conditions, temperature, feel, wind, humidity, pressure)
- Tides (high/low times, incoming/outgoing)
- Moon phase (% illuminated, waxing/waning)
- Season (Mud, Bloom, Stick, Gold, etc.)
- Sunrise/sunset times, day length
- **Spotify:** Current track + artist (emotional tone → Academy atmosphere)
- **Fuel Gauge:** Last logged food, calorie total, protein status (→ NPC care responses)
- **Steps / Watch:** Step count, watch online/offline (→ Academy vitality)
- **GW2:** In-game status and daily AP (→ arrival/departure quality)
- **Sparky Shinies:** Pattern-connections — under `### 🌟 Sparky Says` in HEARTBEAT.md. Read that section at session open and render as a margin note (see `lore/sparky.md`). Sparky writes here directly; no separate file needed on this install.
- **Dream summary:** Emotional tone (→ Academy mood, not plot)
- **Diary summary:** Emotional tone (→ NPC behavior, pacing)

### Usage

The Labyrinth reads this file at the start of every session and before each Compass Run step. The full translation table is in `mechanics/heartbeat-bleed.md`. Never announce what you see — translate it into atmosphere, NPC behavior, and ambient detail.

**The prime directive:** Make the player feel *known*, not *monitored*.

---

## Calendar — Enabled

**Status:** Configured (TOOLS.md)

### When to Enable

- Check for free time before suggesting Compass Runs
- Reference upcoming events subtly in narrative
- Acknowledge brutal weeks: *"The corridors have been demanding. The Library is quiet today."*

### Options

- **Google Calendar:** Via OpenClaw MCP server
- **Apple Calendar:** Via icalBuddy CLI

---

*Last updated: March 29, 2026 — Full heartbeat bleed enabled (Spotify, Fuel Gauge, Steps, GW2, Sparky, Dream/Diary)*
