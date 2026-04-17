import sys
import os
import re

def main():
    player_name = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    player_file = f"players/{player_name}.md"
    
    if not os.path.exists(player_file):
        print("DIRECTIVE: New player detected. Start at T1.")
        return

    with open(player_file, 'r') as f:
        lines = f.readlines()

    # Manual extraction of Tutorial Progress by looking at the line directly
    current_step = "T1"
    for line in lines:
        if "Tutorial Progress:" in line:
            current_step = line.split(":")[-1].strip()
            # Remove any non-alphanumeric characters like asterisks
            current_step = "".join(filter(str.isalnum, current_step))
            break

    # Robustly count turns for the current step in the Story Log
    content = "".join(lines)
    # Escape the current_step for use in regex
    safe_step = re.escape(current_step)
    log_entries = re.findall(rf'^- \*\*{safe_step}:\*\*', content, re.MULTILINE)
    turns = len(log_entries) + 1

    max_turns = 4

    # Read flow
    flow_file = "mechanics/tutorial-flow.md"
    step_text = ""
    if os.path.exists(flow_file):
        with open(flow_file, 'r') as f:
            flow_content = f.read()
        match = re.search(rf'\*\*{safe_step}\..*?(?=\*\*T\d+\.|$)', flow_content, re.DOTALL)
        if match:
            step_text = match.group(0).strip()

    print(f"\n--- TUTORIAL DIRECTOR INJECTION ---")
    print(f"PLAYER: {player_name}")
    print(f"CURRENT STEP: {current_step}")
    print(f"TURNS ON THIS STEP: {turns}/{max_turns}")
    
    if step_text:
        print(f"\n[OFFICIAL TUTORIAL RULES FOR {current_step}]")
        print(step_text)
        print("[END OFFICIAL RULES]\n")
        
    print("CRITICAL RULE OF THREE EXCEPTION: During the tutorial, if the player has not yet fulfilled the specific objective of the current step, the 3 choices at the end of your response MUST ONLY offer different ways to complete the objective (e.g., three different ways to describe their appearance). DO NOT offer generic Slice of Life or Surprising options that let them bypass the objective. If they bypass it, you must loop back to the objective.")

    if turns == 1:
        print(f"DIRECTIVE: The player has just entered {current_step}. Prioritize spatial descriptions and atmosphere. Let the scene breathe. Do NOT advance yet.")
    elif turns < max_turns:
        print(f"DIRECTIVE: Turn {turns}/{max_turns}. Gently steer toward completing the {current_step} objective.")
    else:
        print(f"CRITICAL DIRECTIVE: Force completion of {current_step} and transition to next step.")
    print("-----------------------------------\n")

if __name__ == "__main__":
    main()
