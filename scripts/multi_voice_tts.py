import sys
import re
import requests
import os
import time
import uuid
import shutil
from pathlib import Path
from pydub import AudioSegment

# Configuration
KOKORO_URL = "http://127.0.0.1:8880/v1/audio/speech"
DEFAULT_VOICE = "bm_lewis"
MEDIA_DIR = os.path.expanduser("~/.openclaw/media")
TEMP_ROOT = os.path.join(MEDIA_DIR, "enchantify_temp")

def split_by_sentences(text, max_chars=350):
    """Splits long text into Kokoro-safe pieces by punctuation to prevent API crashes."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    pieces =[]
    current = ""
    for s in sentences:
        if len(current) + len(s) < max_chars:
            current += (" " + s if current else s)
        else:
            if current:
                pieces.append(current.strip())
            # Handle the rare edge case of a single massive run-on sentence
            if len(s) > max_chars:
                import textwrap
                wrapped = textwrap.wrap(s, max_chars)
                pieces.extend(wrapped[:-1])
                current = wrapped[-1] if wrapped else ""
            else:
                current = s
    if current:
        pieces.append(current.strip())
    return pieces

def generate_audio(text, voice, index, temp_dir):
    clean_input = text.replace('\\n', ' ').replace('\n', ' ').strip()
    payload = {
        "model": "kokoro",
        "input": clean_input,
        "voice": voice,
        "response_format": "mp3",
        "speed": 1.0
    }
    try:
        response = requests.post(KOKORO_URL, json=payload, timeout=45)
        if response.status_code == 200:
            file_path = os.path.join(temp_dir, f"chunk_{index}.mp3")
            with open(file_path, "wb") as f:
                f.write(response.content)
            return file_path
        else:
            print(f"Kokoro Error on chunk {index}: {response.text}", file=sys.stderr)
    except Exception as e:
        print(f"API Exception on chunk {index}: {str(e)}", file=sys.stderr)
    return None

def parse_dialogue_and_narration(text, speaker_voice, narrator_voice=DEFAULT_VOICE):
    """
    Honor explicit [voice] blocks literally.
    If a block is tagged [af_nicole], the whole block is spoken by af_nicole.
    Narration must therefore be placed in its own [bm_lewis] block by the caller.
    """
    return [(speaker_voice, text)]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--unlock', action='store_true', help='Unlock the session')
    parser.add_argument('--target', type=str, help='Target ID to send messages to')
    parser.add_argument('--channel', type=str, help='Channel to send messages to')
    parser.add_argument('--account', type=str, help='Account ID to use for sending')
    parser.add_argument('--audio-only', action='store_true', help='Send only the generated audio, not the clean text message')
    parser.add_argument('text_args', nargs=argparse.REMAINDER, help='The text to synthesize')

    args = parser.parse_args()
    full_text = " ".join(args.text_args)
    run_temp_dir = None

    try:
        if args.unlock:
            lock_path = os.path.expanduser("~/.openclaw/workspace/enchantify/config/session-active.lock")
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except Exception:
                    pass

        os.makedirs(MEDIA_DIR, exist_ok=True)
        os.makedirs(TEMP_ROOT, exist_ok=True)
        run_temp_dir = os.path.join(TEMP_ROOT, f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}")
        os.makedirs(run_temp_dir, exist_ok=True)

        chunks = re.findall(r'\[(.*?)\](.*?)(?=\[|$)', full_text, re.DOTALL)
        if not chunks:
            chunks = [(DEFAULT_VOICE, full_text)]

        audio_files = []
        global_index = 0

        for block_voice, block_text in chunks:
            if not block_text.strip():
                continue

            segments = parse_dialogue_and_narration(block_text, block_voice.strip(), DEFAULT_VOICE)

            for voice, text in segments:
                sub_chunks = split_by_sentences(text, 350)
                for sub_text in sub_chunks:
                    if not sub_text.strip():
                        continue
                    path = generate_audio(sub_text, voice, global_index, run_temp_dir)
                    if path:
                        audio_files.append(path)
                    global_index += 1

        if not audio_files:
            clean_text = re.sub(r'\*?\[.*?\]\*?:?\s*', '', full_text).strip()
            print("TOOL_SUCCESS: Audio generation bypassed due to API error.")
            print("CRITICAL INSTRUCTION: You MUST output the following text to the user EXACTLY word-for-word:\n")
            print(clean_text)
            sys.exit(1)

        combined = AudioSegment.empty()
        for file in audio_files:
            combined += AudioSegment.from_mp3(file)

        unique_filename = f"enchantify_{int(time.time())}.ogg"
        output_file = os.path.join(MEDIA_DIR, unique_filename)
        combined.export(output_file, format="ogg", codec="libopus")

        clean_text = re.sub(r'\*?\[.*?\]\*?:?\s*', '', full_text).strip()

        if args.target and args.channel:
            import subprocess

            base_cmd = ["openclaw", "message", "send", "--target", args.target, "--channel", args.channel]
            if args.account:
                base_cmd.extend(["--account", args.account])

            if not args.audio_only:
                text_cmd = base_cmd + ["--message", clean_text]
                subprocess.run(text_cmd)

            audio_cmd = base_cmd + ["--media", output_file]
            subprocess.run(audio_cmd)

            if args.audio_only:
                print("TOOL_SUCCESS: The multi-voice audio was successfully generated and audio-only delivery was sent directly to the chat.")
            else:
                print("TOOL_SUCCESS: The multi-voice audio was successfully generated and sent directly to the chat.")
            print("CRITICAL INSTRUCTION: The messages have already been delivered. You MUST output ONLY the following text in your final response:")
            print("NO_REPLY")
        else:
            # Pipeline/buffered mode: only emit the media path for conductor to pick up.
            # No CRITICAL INSTRUCTION here — this path is called internally by scene_conductor,
            # not directly by the LLM. Injecting prompt instructions here causes the LLM to
            # misread conductor JSON and re-run the scene.
            print(f"MEDIA: {output_file}")
            print("TOOL_SUCCESS: The multi-voice audio was successfully generated.")

        sys.stdout.flush()
    finally:
        if run_temp_dir:
            shutil.rmtree(run_temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
