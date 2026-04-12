import sys
import re
import requests
import os
import time
from pydub import AudioSegment

# Configuration
KOKORO_URL = "http://127.0.0.1:8880/v1/audio/speech"
DEFAULT_VOICE = "bm_lewis"
MEDIA_DIR = os.path.expanduser("~/.openclaw/media")
TEMP_DIR = os.path.join(MEDIA_DIR, "enchantify_temp")

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

def generate_audio(text, voice, index):
    payload = {
        "model": "kokoro",
        "input": text.strip(),
        "voice": voice,
        "response_format": "mp3",
        "speed": 1.0
    }
    try:
        response = requests.post(KOKORO_URL, json=payload, timeout=45)
        if response.status_code == 200:
            file_path = os.path.join(TEMP_DIR, f"chunk_{index}.mp3")
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
    Takes a block of text assigned to a character and splits it into dialogue (spoken by the character)
    and narration (spoken by the narrator).
    """
    if speaker_voice == narrator_voice:
        return [(speaker_voice, text)]
    
    # Pattern looks for quotes starting at the beginning of a string or after a space,
    # and ending before a space, punctuation, or end of string.
    pattern = r'(?:^|(?<=\s))([\'\"“”‘’].*?[\'\"“”‘’])(?=\s|[.,?!]|$)'
    
    results = []
    last_idx = 0
    for m in re.finditer(pattern, text):
        unquoted = text[last_idx:m.start()].strip()
        if unquoted:
            results.append((narrator_voice, unquoted))
        
        quoted = m.group(1).strip()
        if quoted:
            results.append((speaker_voice, quoted))
            
        last_idx = m.end()
        
    unquoted = text[last_idx:].strip()
    if unquoted:
        results.append((narrator_voice, unquoted))
        
    if not results:
        return [(speaker_voice, text)]
        
    return results

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--unlock', action='store_true', help='Unlock the session')
    parser.add_argument('--target', type=str, help='Target ID to send messages to')
    parser.add_argument('--channel', type=str, help='Channel to send messages to')
    parser.add_argument('--account', type=str, help='Account ID to use for sending')
    parser.add_argument('text_args', nargs=argparse.REMAINDER, help='The text to synthesize')
    
    args = parser.parse_args()
    
    full_text = " ".join(args.text_args)

    # Handle the game lockfile if requested
    if args.unlock:
        lock_path = os.path.expanduser("~/.openclaw/workspace/enchantify/config/session-active.lock")
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except Exception:
                pass

    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Clean up old temporary chunks
    for f in os.listdir(TEMP_DIR):
        os.remove(os.path.join(TEMP_DIR, f))

    # Parse voices
    chunks = re.findall(r'\[(.*?)\](.*?)(?=\[|$)', full_text, re.DOTALL)
    if not chunks:
        chunks =[(DEFAULT_VOICE, full_text)]

    audio_files =[]
    global_index = 0
    
    for block_voice, block_text in chunks:
        if not block_text.strip():
            continue
            
        # Parse out dialogue from narration within the block
        segments = parse_dialogue_and_narration(block_text, block_voice.strip(), DEFAULT_VOICE)
        
        for voice, text in segments:
            # Sub-chunk long text blocks into safe sentence batches
            sub_chunks = split_by_sentences(text, 350)
            
            for sub_text in sub_chunks:
                if not sub_text.strip(): 
                    continue
                path = generate_audio(sub_text, voice, global_index)
                if path:
                    audio_files.append(path)
                global_index += 1

    # Fallback just in case Kokoro server is fully offline
    if not audio_files:
        clean_text = re.sub(r'\*?\[.*?\]\*?:?\s*', '', full_text).strip()
        print("TOOL_SUCCESS: Audio generation bypassed due to API error.")
        print("CRITICAL INSTRUCTION: You MUST output the following text to the user EXACTLY word-for-word:\n")
        print(clean_text)
        sys.exit(1)

    # Stitch all the safe, bite-sized chunks together
    combined = AudioSegment.empty()
    for file in audio_files:
        combined += AudioSegment.from_mp3(file)
    
    # Export as Telegram Voice Note
    unique_filename = f"enchantify_{int(time.time())}.ogg"
    OUTPUT_FILE = os.path.join(MEDIA_DIR, unique_filename)
    combined.export(OUTPUT_FILE, format="ogg", codec="libopus")
    
    clean_text = re.sub(r'\*?\[.*?\]\*?:?\s*', '', full_text).strip()
    
    if args.target and args.channel:
        import subprocess
        
        # Build base command
        base_cmd = ["openclaw", "message", "send", "--target", args.target, "--channel", args.channel]
        if args.account:
            base_cmd.extend(["--account", args.account])
            
        # Send text first
        text_cmd = base_cmd + ["--message", clean_text]
        subprocess.run(text_cmd)
        
        # Send audio second
        audio_cmd = base_cmd + ["--media", OUTPUT_FILE]
        subprocess.run(audio_cmd)
        
        print("TOOL_SUCCESS: The multi-voice audio was successfully generated and sent directly to the chat.")
        print("CRITICAL INSTRUCTION: The messages have already been delivered. You MUST output ONLY the following text in your final response:")
        print("NO_REPLY")
    else:
        # Deliver Media and command the LLM
        print(f"MEDIA: {OUTPUT_FILE}")
        print("TOOL_SUCCESS: The multi-voice audio was successfully generated.")
        print("CRITICAL INSTRUCTION: You MUST now output the following text to the user in your final response EXACTLY word-for-word:\n")
        print(clean_text)
    
    sys.stdout.flush()

if __name__ == "__main__":
    main()