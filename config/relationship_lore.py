"""Curated social graph: cliques, rivalries, faculty politics, cross-chapter bonds.

Imported by relationship_generator.py. Edit here, then run:
  python3 scripts/relationships.py generate bj
"""

from __future__ import annotations

# chapter → generator tuning
CHAPTER_PROFILES: dict[str, dict[str, int]] = {
    "Riddlewind": {"intra_bonus": 10, "cross_bonus": 4},
    "Emberheart": {"intra_bonus": 0, "rivalry_bonus": 15},
    "Mossbloom": {"intra_bonus": 12, "cross_bonus": 6},
    "Tidecrest": {"intra_bonus": 8, "cross_bonus": 5},
}

# Named cliques: members get close_friend mesh (strength from clique)
CLIQUES: list[dict] = [
    {
        "name": "Riddlewind Puzzle Court",
        "members": ["Ellie Moons", "Soren Ng", "Lyra Stanford", "Orlando “Oracle” Scrollstone"],
        "stance": "close_friend",
        "strength": 78,
        "notes": "Puzzles, prophecy, and late stacks.",
    },
    {
        "name": "Riddlewind Notice Pranksters",
        "members": ["Cedric Widden", "Felix Quimby", "Wilbur “Wordplay” Lexi"],
        "stance": "close_friend",
        "strength": 72,
        "notes": "Harmless pranks and competitive puns.",
    },
    {
        "name": "Riddlewind Soft Circle",
        "members": ["Aria Silverthorn", "Serenity Lightfeather", "Felicity “Fable” Grimmhaven"],
        "stance": "close_friend",
        "strength": 70,
        "notes": "Gentle students who find each other in loud corridors.",
    },
    {
        "name": "Emberheart Forge Pair",
        "members": ["Rowan Laraway", "Caspian Shan"],
        "stance": "ally",
        "strength": 68,
        "notes": "Makers and shadows; trade favors quietly.",
    },
    {
        "name": "Emberheart Blaze Trio",
        "members": ["Isolde Firare", "Lila Woods", "Brianna Clarke"],
        "stance": "creative_rival",
        "strength": 62,
        "notes": "Competitive fire; respect through sparring.",
    },
    {
        "name": "Mossbloom Hearth",
        "members": ["Min-seo Kim", "Ivy Liversedge", "Briar Merlock"],
        "stance": "close_friend",
        "strength": 76,
        "notes": "Food, herbs, and patient care.",
    },
    {
        "name": "Mossbloom Quiet Watch",
        "members": ["Jasper Blum", "Lysander Mosswood", "Astrid Natsune"],
        "stance": "ally",
        "strength": 65,
        "notes": "Observers who trust silence.",
    },
    {
        "name": "Tidecrest Explorer Deck",
        "members": ["Orion Watson", "Dylan Williamson", "Marina Clockhouse"],
        "stance": "close_friend",
        "strength": 74,
        "notes": "Weather, water, and daredevil charts.",
    },
    {
        "name": "Tidecrest Dream Choir",
        "members": ["Aurora Whispers", "Lara Rourck", 'Octavius "Ode" Quillenchant'],
        "stance": "close_friend",
        "strength": 71,
        "notes": "Tarot tones and soulful tides.",
    },
    {
        "name": "Tidecrest Player Circle",
        "members": ["Zara Finch", "Serenity Brown", "Ignatius “Inkwell” Scribblesnap"],
        "stance": "close_friend",
        "strength": 73,
        "notes": "Stories, games, and meticulous notes.",
    },
]

# Explicit edges: a, b, stance, strength, notes
CURATED_EDGES: list[tuple[str, str, str, int, str]] = [
    # ── Cross-chapter student bonds & frictions ──
    ("Finn Bridges", "Damien Nights", "respectful_rival", 58, "Emberheart honor vs Riddlewind shadow."),
    ("Zara Finch", "Ellie Moons", "ally", 55, "Swap thrift finds and puzzle clues."),
    ("Serenity Brown", "Felix Quimby", "ally", 52, "Speed-run errands together for fun."),
    ("Serenity Brown", "Serenity Lightfeather", "name_confusion", 45, "Perpetual mistaken identity; fond exasperation."),
    ("Wicker Eddies", "Orlando “Oracle” Scrollstone", "suspects", 50, "Oracle reads his timelines; Wicker hates being predicted."),
    ("Brianna Clarke", "Cedric Widden", "creative_rival", 48, "Graffiti ethos vs street-magic pranks."),
    ("Lila Woods", "Ignatius “Inkwell” Scribblesnap", "admires", 55, "She reviews restaurants; he formats the reviews."),
    ("Min-seo Kim", "Aria Silverthorn", "ally", 58, "Community garden volunteers across chapters."),
    ("Anton Smith", "Soren Ng", "study_partner", 60, "Archives and riddles until midnight."),
    ("Gwendolyn Mythwright", "Felicity “Fable” Grimmhaven", "ally", 62, "Folklore and urban legend hunts."),
    ("Raven Hearts", "Caspian Shan", "suspects", 52, "Both watch from edges; neither trusts the other's silence."),
    ("Melisande Blackwood", "Lyra Stanford", "rivalry", 50, "Cold ambition vs starry intuition."),
    ("Selene Moonfall", "Aurora Whispers", "ally", 54, "Mystique and tarot gossip."),
    ("Selene Moonfall", "Zara Finch", "suspects", 48, "Selene thinks Zara sees too much."),
    ("Astra Sonseur", "Aria Silverthorn", "admires", 50, "Sunlight encouraging shy kindness."),
    ("Thorn Thomas", "Felix Quimby", "ally", 45, "Animals and parkour — odd but sincere."),
    # ── Emberheart internal drama ──
    ("Wicker Eddies", "Brianna Clarke", "admires", 55, "Useful chaos; she keeps her own manifesto."),
    ("Wicker Eddies", "Isolde Firare", "creative_rival", 58, "Two alphas in one chapter."),
    ("Wicker Eddies", "Astra Sonseur", "suspects", 52, "Optimism irritates his business model."),
    ("Finn Bridges", "Isolde Firare", "rivalry", 55, "Sparring respect; neither yields."),
    ("Finn Bridges", "Melisande Blackwood", "suspects", 60, "He knows she's crew; she knows he knows."),
    ("Finn Bridges", "Brianna Clarke", "ally", 42, "Grudging respect for honest rebellion."),
    ("Lila Woods", "Rowan Laraway", "ally", 50, "She feeds the makers; they fix her kettle."),
    # ── Riddlewind ──
    ("Damien Nights", "Soren Ng", "ally", 48, "Night routes and cold case files."),
    ("Damien Nights", "Wilbur “Wordplay” Lexi", "rivalry", 44, "Drama vs puns."),
    ("Ellie Moons", "Felix Quimby", "study_partner", 56, "Geocache speed trials."),
    ("Lyra Stanford", "Aria Silverthorn", "protectorate", 58, "Lyra reads the stars; Aria reads the room."),
    # ── Mossbloom ──
    ("Clarissa “Clio” Quibblesnatch", "Anton Smith", "admires", 52, "Poetry vs archives — tragic affection."),
    ("Gwendolyn Mythwright", "Thorn Thomas", "ally", 54, "Cryptids and veterinary clinics."),
    ("Professor Archibald Permancer", "Evelyn Riad", "ally", 62, "Dark archives; shared paranoia."),
    ("Archibald Evergreen", "Anton Smith", "mentor", 65, "Library stacks and silence."),
    ("Archibald Evergreen", "Evelyn Riad", "professional", 55, "Head librarian and Nothing researcher."),
    # ── Tidecrest ──
    ("Orion Watson", "Zara Finch", "admires", 50, "He brags; she listens for the true story."),
    ("Marina Clockhouse", "Professor Eleanor Euphony", "teachers_pet", 68, "Tidal acoustics and tuning forks."),
    ("Dylan Williamson", "Professor Ignatius Imatook", "faculty_favorite", 55, "Storms and weather witchery."),
    ("Professor Vivian Villanelle", "Penny Blackletter", "ally", 64, "Ink-binding meets the Margins Desk."),
    # ── Faculty politics & pedagogy ──
    ("Professor Elara Nightshade", "Professor Cedric Stonebrook", "philosophical_rival", 48, "Competition vs stillness — civil in hallways."),
    ("Professor Elara Nightshade", "Headmaster Orion Blackthorn", "ally", 58, "Emberheart visionaries."),
    ("Professor Luna Wispwood", "Professor Eleanor Euphony", "colleague", 55, "Tidecrest explorers who trade field notes."),
    ("Professor Lydia Boggle", "Professor Wellend Thickets", "colleague", 60, "Riddlewind cooperation — not quite trust."),
    ("Professor Thaddeus Mook", "Professor Lydia Boggle", "rivalry", 42, "Puns vs polysyllables."),
    ("Professor Archibald Permancer", "Professor Ignatius Imatook", "colleague", 50, "Mossbloom eccentrics."),
    ("Professor Kyle Momort", "Professor Cedric Stonebrook", "suspects", 52, "Escape routes vs beginner's mind."),
    ("Professor Kyle Momort", "Professor Maxwell Thorne", "hidden_alliance", 58, "Emberheart shadows."),
    ("Professor Wellend Thickets", "Professor Lydia Boggle", "suspects", 45, "Cooperation cover; he studies her games."),
    ("Headmistress Seraphina Thorne", "Professor Wellend Thickets", "professional", 55, "Cordial; she measures his riddles."),
    ("Headmistress Seraphina Thorne", "Headmaster Orion Blackthorn", "philosophical_rival", 50, "Innovation vs narrative weight."),
    ("Headmaster Orion Blackthorn", "Professor Elara Nightshade", "ally", 55, "Emberheart alignment."),
    ("Professor Bastion Goldweaver", "Professor Vivian Villanelle", "colleague", 52, "Craft and commerce."),
    ("Gimble of the Errata Registry", "Bellkeeper Elian Quill", "ally", 58, "Registry clerks respect punctuality."),
    ("Dr. Elowen Vellum", "Dr. Selene Inkrest", "colleague", 62, "Body before story; shared patients."),
    ("Dr. Selene Inkrest", "Professor Cedric Stonebrook", "ally", 50, "Stillness supports therapy."),
    # ── Wicker crew cross-chapter ──
    ("Damien Nights", "Wicker Eddies", "loyal_crew", 82, "Crew anchor across chapters."),
    ("Raven Hearts", "Selene Moonfall", "ally", 56, "Crew coordination; Tidecrest/Mossbloom."),
    ("Raven Hearts", "Damien Nights", "loyal_crew", 75, "Shadow work."),
    # ── Benefactors & pressure ──
    ("Victor Ebonheart", "Wicker Eddies", "admires", 45, "Transactional interest; never wholesome."),
    ("Eleanor Whitewood", "Zara Finch", "admires", 40, "Patron taste for quiet loyalty."),
    ("Victor Ebonheart", "Headmistress Seraphina Thorne", "professional", 50, "Old money and old stories."),
    # ── Guardians & chapters ──
    ("Letitia Windings", "Professor Wellend Thickets", "ally", 55, "Cooperation ethos."),
    ("Erik Forgeton", "Professor Elara Nightshade", "ally", 52, "Emberheart individuality."),
    ("Sylvia Deep", "Professor Cedric Stonebrook", "ally", 58, "Stillness kinship."),
    ("Harry Ono", "Professor Luna Wispwood", "ally", 54, "Spontaneity kinship."),
    # ── Library triangle ──
    ("Quentin Pagester", "Penny Blackletter", "rivalry", 46, "Catalog vs headline."),
    ("Quentin Pagester", "Ignatius “Inkwell” Scribblesnap", "ally", 55, "Formatting religion."),
    # ── Professor ↔ student favorites & frictions (rich web) ──
    ("Professor Luna Wispwood", "Orion Watson", "faculty_favorite", 62, "Exploration appetite."),
    ("Professor Luna Wispwood", "Dylan Williamson", "faculty_favorite", 58, "Weather daredevil."),
    ("Professor Luna Wispwood", "Selene Moonfall", "faculty_wary", 52, "Too much social climbing."),
    ("Professor Eleanor Euphony", "Lara Rourck", "teachers_pet", 64, "Voice like an instrument."),
    ("Professor Eleanor Euphony", "Aurora Whispers", "ally", 55, "Mystic frequencies."),
    ("Professor Vivian Villanelle", "Octavius “Ode” Quillenchant", "teachers_pet", 66, "Earnest poetry worth binding."),
    ("Professor Vivian Villanelle", "Zara Finch", "admires", 58, "One perfect souvenir sentence."),
    ("Professor Ignatius Imatook", "Astrid Natsune", "faculty_favorite", 54, "Cloud augury daydreams."),
    ("Professor Ignatius Imatook", "Jasper Blum", "faculty_wary", 45, "Too guarded to argue with the sky."),
    ("Professor Lydia Boggle", "Felix Quimby", "admires", 50, "Speed is a Notice prompt."),
    ("Professor Lydia Boggle", "Soren Ng", "ally", 52, "Riddles are glints."),
    ("Professor Wellend Thickets", "Ellie Moons", "faculty_favorite", 60, "Useful obsession with puzzles."),
    ("Professor Wellend Thickets", "Orlando “Oracle” Scrollstone", "suspects", 55, "Predictions complicate his games."),
    ("Professor Maxwell Thorne", "Caspian Shan", "admires", 50, "Shadow as metaphor."),
    ("Professor Maxwell Thorne", "Wicker Eddies", "suspects", 48, "Allegory with teeth."),
    ("Professor Elara Nightshade", "Rowan Laraway", "admires", 52, "Invention with spine."),
    ("Professor Elara Nightshade", "Caspian Shan", "faculty_wary", 44, "Too hidden for exhibition culture."),
    ("Professor Kyle Momort", "Brianna Clarke", "faculty_favorite", 56, "Rebellion he can steer."),
    ("Professor Kyle Momort", "Aria Silverthorn", "faculty_wary", 50, "Kindness is hard to corrupt."),
    ("Professor Archibald Permancer", "Gwendolyn Mythwright", "teachers_pet", 62, "Monsters and footnotes."),
    ("Professor Archibald Permancer", "Raven Hearts", "suspects", 58, "Crew in Mossbloom soil."),
    ("Professor Cedric Stonebrook", "Lysander Mosswood", "mentor", 68, "Walks without agenda."),
    ("Professor Cedric Stonebrook", "Min-seo Kim", "admires", 55, "Feeding people is rest."),
    ("Professor Cedric Stonebrook", "Damien Nights", "faculty_wary", 48, "Drama disturbs stillness."),
    # ── Slow-burn / gentle crush textures (age-appropriate) ──
    ("Octavius “Ode” Quillenchant", "Zara Finch", "crush", 48, "Writes poems he never delivers."),
    ("Cedric Widden", "Marina Clockhouse", "crush", 45, "Pranks stop when she listens."),
    ("Anton Smith", "Lyra Stanford", "admires", 46, "Stars seem easier than people."),
    ("Jasper Blum", "Ivy Liversedge", "protectorate", 52, "Silent guard near the herb garden."),
    # ── Mossbloom & Riddlewind extra threads ──
    ("Ivy Liversedge", "Professor Cedric Stonebrook", "admires", 50, "Stillness as medicine."),
    ("Lysander Mosswood", "Briar Merlock", "close_friend", 68, "Trail wisdom shared."),
    ("Thorn Thomas", "Min-seo Kim", "ally", 56, "Animals and kitchen gardens."),
    ("Raven Hearts", "Professor Archibald Permancer", "suspects", 54, "Both catalog dark corners."),
    ("Felix Quimby", "Damien Nights", "rivalry", 46, "Parkour vs brooding."),
    ("Soren Ng", "Professor Thaddeus Mook", "faculty_wary", 48, "Vocabulary as armor."),
    ("Wilbur “Wordplay” Lexi", "Professor Lydia Boggle", "teachers_pet", 60, "Pun apprenticeship."),
    ("Cedric Widden", "Professor Lydia Boggle", "teachers_pet", 65, "Already canon; reinforced."),
    # ── Tidecrest rivalries & loyalties ──
    ("Selene Moonfall", "Orion Watson", "rivalry", 50, "Social climb vs honest exploration."),
    ("Dylan Williamson", "Lara Rourck", "ally", 54, "Storm and song."),
    ("Aurora Whispers", "Marina Clockhouse", "close_friend", 62, "Mystic tides."),
    ("Ignatius “Inkwell” Scribblesnap", "Professor Vivian Villanelle", "admires", 58, "Structure envy."),
    # ── Book Fae & support staff ──
    ("Gimble of the Errata Registry", "Dr. Elowen Vellum", "colleague", 50, "Body and ledger both need accuracy."),
    ("Dr. Elowen Vellum", "Professor Cedric Stonebrook", "ally", 52, "Rest supports longevity."),
    ("Index", "Quentin Pagester", "ally", 45, "Catalog assistance."),
    ("Bellkeeper Elian Quill", "Penny Blackletter", "ally", 48, "Deadlines and Today's Page."),
]

# Extra agenda texture for major cast
AGENDA_LORE: dict[str, dict[str, object]] = {
    "Finn Bridges": {
        "goal": "Stay unowned by any faction while proving he can stand alone.",
        "fear": "Needing someone who could leave.",
        "watching": ["Wicker Eddies", "Zara Finch"],
        "if_absent_24h": "Oil his hiking boots and leave them outside Emberheart with no note.",
    },
    "Ellie Moons": {
        "goal": "Solve one real-world puzzle that proves the Academy bleeds into town.",
        "fear": "A riddle with no answer.",
        "watching": ["Soren Ng", "Orlando “Oracle” Scrollstone"],
        "if_absent_24h": "Pin a geocache clue to the Riddlewind board with too much enthusiasm.",
    },
    "Professor Elara Nightshade": {
        "goal": "Win the next inter-chapter exhibition without cheating — probably.",
        "fear": "Mossbloom stillness infecting her students.",
        "watching": ["Isolde Firare", "Professor Cedric Stonebrook"],
        "if_absent_24h": "Leave a challenge glove on the dueling floor.",
    },
    "Professor Cedric Stonebrook": {
        "goal": "Keep one student from burning out this week.",
        "fear": "Being forced to shout.",
        "watching": ["Headmistress Seraphina Thorne", "Anton Smith"],
        "if_absent_24h": "Place a single smooth stone on a mossy windowsill with no explanation.",
    },
    "Professor Wellend Thickets": {
        "goal": "Advance the cooperative cover story while the real game continues.",
        "fear": "A student who asks the right question too early.",
        "watching": ["Professor Kyle Momort", "Soren Ng"],
        "if_absent_24h": "Replace one cooperative poster with a riddle only three students will solve.",
    },
    "Damien Nights": {
        "goal": "Map where the Nothing feels thin near industrial edges.",
        "fear": "Being seen caring.",
        "watching": ["Wicker Eddies", "Raven Hearts"],
        "if_absent_24h": "Chalk a shadow diagram on a Riddlewind stair that moves at dusk.",
    },
    "Melisande Blackwood": {
        "goal": "Protect Wicker's position without visible devotion.",
        "fear": "Finn Bridges naming her loyalty aloud.",
        "watching": ["Wicker Eddies", "Finn Bridges"],
        "if_absent_24h": "Leave a corporate news clipping where only Emberheart will find it.",
    },
    "Min-seo Kim": {
        "goal": "Feed someone who forgot to eat.",
        "fear": "Harsh words in the greenhouse.",
        "watching": ["Ivy Liversedge", "Aria Silverthorn"],
        "if_absent_24h": "Leave herb tea outside a dorm with no name — only a leaf drawing.",
    },
    "Orion Watson": {
        "goal": "Chart a trail no student has bragged about yet.",
        "fear": "Calm seas.",
        "watching": ["Dylan Williamson", "Zara Finch"],
        "if_absent_24h": "Tie a rope knot on the Tidecrest rail that means 'new route'.",
    },
    "Penny Blackletter": {
        "goal": "Rescue one beautiful moment from vanishing unprinted.",
        "fear": "A headline that hurts the player.",
        "watching": ["Professor Bastion Goldweaver", "Professor Vivian Villanelle"],
        "if_absent_24h": "Stamp PUBLIC-SAFE on a margin draft and leave it for BJ.",
    },
}
