import subprocess

with open('lore/characters.md', 'r') as f:
    text = f.read()

names = []
for line in text.split('\n'):
    line = line.strip()
    if line.startswith('### '):
        name = line[4:].split('(')[0].split('—')[0].strip()
        names.append(name)
    elif line.startswith('**') and '—' in line:
        name = line[2:].split('**')[0].strip()
        names.append(name)
    elif line.startswith('**') and '(' in line:
        name = line[2:].split('**')[0].strip()
        names.append(name)

with open('lore/world-register.md', 'r') as f:
    reg = f.read()

added = 0
for name in names:
    first_name = name.split()[0]
    if first_name not in reg and name not in reg:
        if "Thorne" in name or "Boggle" in name or "Archibald" in name or "Wicker" in name or "Zara" in name or "Stonebrook" in name or "Euphony" in name:
            continue
        print(f"Adding {name}...")
        subprocess.run(["python3", "scripts/write-entity.py", name, "NPC", "5", "[thread:academy-daily] Routine Academy presence."])
        added += 1

print(f"Added {added} characters.")
