# App Register — Talisman Control Ledger

*The current state of the app territory war. Updated by `scripts/pact-engine.py` during world ticks.*
*Never edit Control Belief directly — the engine manages it. You can add new app rows.*

---

## Control Tiers (reference)
- **1–9:** Contesting | **10–24:** Influenced | **25–44:** Controlled | **45–69:** Dominated | **70+:** Sovereign

---

## Apps

| App | System | Natural Alignment | Emberheart | Mossbloom | Riddlewind | Tidecrest | Duskthorn | Controller |
|---|---|---|---|---|---|---|---|---|
| Apple Notes | productivity | Emberheart | 17 | 14 | 6 | 9 | 7 | Emberheart (Influenced) |
| Apple Reminders | productivity | Riddlewind | 8 | 11 | 16 | 5 | 7 | Riddlewind (Influenced) |
| Apple Calendar | productivity | Riddlewind | 11 | 7 | 17 | 6 | 4 | Riddlewind (Influenced) |
| Obsidian | productivity | Mossbloom | 13 | 21 | 7 | 4 | 3 | Mossbloom (Influenced) |
| Moltbook | social | Emberheart | 21 | 5 | 8 | 16 | 16 | Emberheart (Influenced) |
| Bluesky | social | Riddlewind | 11 | 6 | 14 | 13 | 12 | Riddlewind (Influenced) |
| X / Twitter | social | Duskthorn | 7 | 3 | 8 | 14 | 25 | Duskthorn (Controlled) |
| Reddit | social | Riddlewind | 6 | 4 | 17 | 10 | 17 | Riddlewind (Influenced) |
| Spotify | music | Tidecrest | 7 | 17 | 8 | 18 | 5 | Tidecrest (Influenced) |
| Telegram | messaging | Tidecrest | 8 | 5 | 14 | 13 | 11 | Riddlewind (Influenced) |
| iMessage | messaging | Riddlewind | 11 | 7 | 13 | 12 | 5 | Riddlewind (Influenced) |
| Apple Mail | messaging | Riddlewind | 14 | 6 | 18 | 9 | 8 | Riddlewind (Influenced) |
| Safari | browser | Riddlewind | 8 | 10 | 16 | 12 | 14 | Riddlewind (Influenced) |

---

## Last Pact Actions

- **[Pact War: Duskthorn]** push on **Spotify** (4→5) — Duskthorn presses further into Spotify. It has been watching.
- **[Pact War: Riddlewind]** push on **Spotify** (5→8) — Riddlewind weaves deeper into Spotify. Another thread added to the pattern.
- **[Pact War: Mossbloom]** push on **Spotify** (14→17) — Mossbloom settles further into Spotify. Patience is its weapon.
- **[Pact War: Tidecrest]** push on **Reddit** (9→10) — Tidecrest surges in Reddit. The moment was right and it moved.
- **[Pact War: Duskthorn]** challenge on **Bluesky** (11→12) — Duskthorn begins a pressure campaign against Riddlewind in Bluesky.
- **[Pact War: Duskthorn]** consolidate on **X / Twitter** (23→25) — **reaches Controlled** — Duskthorn tightens its grip on X / Twitter. Territory held is leverage.
- **[Pact War: Tidecrest]** push on **Moltbook** (13→16) — Tidecrest surges in Moltbook. The moment was right and it moved.
*Filled in by pact-engine.py after each tick. Most recent first.*

---

## Notes

- **Obsidian** is Mossbloom's strongest position at game start (21), but still Influenced. Controlled tier requires 25.
- **Moltbook** is nominally Emberheart's but Duskthorn is close behind. This is the most active contest.
- **X / Twitter** is Duskthorn's natural home and its strongest non-Obsidian position. Tidecrest is the main challenger.
- **Reddit** appears Riddlewind-controlled but Duskthorn is close. It will raid when its overall Belief is strong enough.
- **Apple Mail** is Riddlewind's strongest messaging position. Emberheart contests it for urgency and action.
- **Safari** is Riddlewind's web territory. Duskthorn is already close (14) — it knows the dark corners of the web.
- **Social apps without accounts (Reddit, X, Bluesky):** read/search/draft actions work now. Post actions require credentials — wire via `config/secrets.env` when ready.
- Player can invest Belief directly into specific talisman-app control — see `lore/belief-investments.md`.
