# Multi-Voice TTS Skill

This skill allows the Labyrinth to generate high-fidelity, multi-voice audio by orchestrating the Kokoro TTS server and stitching the results.

## When to Use
- Whenever the narrative includes multiple speakers.
- When a scene requires high-fidelity "Stitched" audio instead of the default single-voice TTS.

## How to Call
1. Construct the full narrative text using bracketed voice tags. These tags should match character names or voice IDs from `config/voice-assignments.md`.
2. Call the tool via `exec`: `python3 scripts/multi_voice_tts.py "[Voice Name or ID] Text..."`
3. The script will look up the correct voice in the config, generate the audio, and output the cleaned text plus the `MEDIA:` tag.
4. **CRITICAL:** Do NOT narrate the tool call. The script will return a `TOOL_SUCCESS` message along with the cleaned text. You MUST output exactly the text the tool provides in your final response so the user can read along. Do NOT summarize or skip anything.

## Voice Lookup Registry
The Labyrinth dynamically reads `config/voice-assignments.md` to map names to vocal inks. Common examples include:
- [Labyrinth] or [bm_lewis] - The Narrator
- [Sparky] or [am_echo] - Margin Notes
- [Zara Finch] or [af_sarah] - Student
- [Professor Boggle] or [bf_alice] - Faculty
- [Finn Stonebrook] or [am_adam] - Student
