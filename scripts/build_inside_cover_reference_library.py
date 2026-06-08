#!/usr/bin/env python3
"""Build the local reference library used by the Inside Cover iOS app."""

from __future__ import annotations

import json
import re
import importlib.util
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ios" / "InsideCover" / "Shared" / "BookReferenceLibrary.json"
PATREON_URL = "https://patreon.com/thedoobaleedoos"

WONDER_DIR = ROOT / "lore" / "wonder-compass-book"
CHARACTER_VISUALS = ROOT / "lore" / "character-visuals.json"
LORE_FILES = [
    ROOT / "lore" / "characters.md",
    ROOT / "lore" / "belief-system.md",
    ROOT / "lore" / "belief-investments.md",
    ROOT / "lore" / "belief-combat.md",
    ROOT / "lore" / "wonder-compass.md",
    ROOT / "lore" / "compass-directions.md",
    ROOT / "lore" / "compass-run.md",
    ROOT / "lore" / "outer-stacks.md",
    ROOT / "lore" / "ley-lines.md",
    ROOT / "lore" / "locations.md",
    ROOT / "lore" / "threads.md",
    ROOT / "lore" / "chapters.md",
    ROOT / "lore" / "school-life.md",
    ROOT / "lore" / "academy-events.md",
    ROOT / "lore" / "world.md",
    ROOT / "lore" / "the-pitch.md",
]

CURATED_ENCHANTIFY_LORE = [
    {
        "id": "labyrinth-lore-book-of-you",
        "sourceID": "labyrinth-lore",
        "title": "The Book of You",
        "prompt": "Let today become a page worth keeping.",
        "body": "The Book of You is the private volume that waits closest to the reader. It does not demand grand adventures. It notices the cup left beside the bed, the weather at the window, the sentence that would have vanished if no one had written it down. When a page is kept, the Book does not announce a score. It simply grows warmer, as if one more lamp has been lit in a long room.",
        "tags": ["labyrinth-lore", "book-of-you", "memory", "private", "rooms"],
    },
    {
        "id": "labyrinth-lore-outer-stacks",
        "sourceID": "labyrinth-lore",
        "title": "The Outer Stacks",
        "prompt": "Let a place become a room.",
        "body": "Beyond the Academy's catalogued halls are the Outer Stacks, where real places gather room-feelings. A harbor may become a tidal reading room. A cafe may keep a tiny kingdom beneath the sugar packets. A parking lot may hold a door that only appears when the light hits the asphalt correctly. The Outer Stacks do not make places less real. They make them more themselves.",
        "tags": ["labyrinth-lore", "outer-stacks", "location", "rooms", "place"],
    },
    {
        "id": "labyrinth-lore-weather",
        "sourceID": "labyrinth-lore",
        "title": "Weather in the Stacks",
        "prompt": "Let the sky annotate the page.",
        "body": "Weather at the Academy is never only meteorological, but it is never merely symbolic either. Fog makes professors cancel class to watch the harbor disappear by degrees. Rain turns corridors into quieter arguments. Bright cold sharpens the ink. Heat makes the paper curl and the students theatrical. The Library cloud above the great ceiling changes color when the building is thinking about something it does not intend to say aloud.",
        "tags": ["labyrinth-lore", "atmosphere", "school", "weather", "world"],
    },
]

LABYRINTH_LORE_SNIPPETS = [
    {
        "id": "labyrinth-character-seraphina-thorne",
        "sourceID": "labyrinth-lore",
        "title": "Headmistress Seraphina Thorne",
        "prompt": "Meet the woman who keeps the doors opening.",
        "body": "Seraphina Thorne is the Academy's headmistress: elegant, dry-witted, and nearly impossible to surprise. Students describe her as someone who can make a reprimand feel like a riddle and a kindness feel like a secret door. She believes wonder must be practiced, not merely admired, and that a school for magic should teach students how to notice the world before they try to change it.",
        "tags": ["labyrinth-lore", "character", "faculty", "headmistress", "academy"],
    },
    {
        "id": "labyrinth-character-orion-blackthorn",
        "sourceID": "labyrinth-lore",
        "title": "Orion Blackthorn",
        "prompt": "Notice the professor who listens before he speaks.",
        "body": "Orion Blackthorn is a professor of practical magic and quiet rescue. He has the air of someone who has read the dangerous books and put several of them back without boasting. Students trust him because he does not hurry their fear. He teaches that attention is a spell, courage is a habit, and the safest path through the Labyrinth is rarely the straightest one.",
        "tags": ["labyrinth-lore", "character", "faculty", "magic", "mentor"],
    },
    {
        "id": "labyrinth-character-elara-nightshade",
        "sourceID": "labyrinth-lore",
        "title": "Professor Elara Nightshade",
        "prompt": "Step into the greenhouse after dusk.",
        "body": "Elara Nightshade teaches the living side of magic: plants that answer tone, roots that keep old grudges, vines that climb toward secrets instead of light. Her classroom smells of damp soil, bitter leaves, and chalk dust. She is stern with carelessness and tender with anything trying to grow, which includes plants, students, and occasionally stubborn professors.",
        "tags": ["labyrinth-lore", "character", "faculty", "plants", "classes"],
    },
    {
        "id": "labyrinth-character-kyle-momort",
        "sourceID": "labyrinth-lore",
        "title": "Professor Kyle Momort",
        "prompt": "Listen for the joke under the lecture.",
        "body": "Kyle Momort has the dangerous gift of making impossible subjects feel like parlor tricks until the trick opens a staircase. His lessons move quickly, often sideways, and occasionally through furniture. Students leave his class with singed cuffs, better questions, and the uneasy suspicion that the punchline was also the point.",
        "tags": ["labyrinth-lore", "character", "faculty", "classes", "magic"],
    },
    {
        "id": "labyrinth-character-cedric-stonebrook",
        "sourceID": "labyrinth-lore",
        "title": "Professor Cedric Stonebrook",
        "prompt": "Learn why the Compass starts with a small question.",
        "body": "Cedric Stonebrook teaches Compass work with the patience of a trail marker. He is less interested in impressive adventures than in complete ones: Notice, Embark, Sense, Write, then return to Rest. His students learn that a five-minute loop around a room can be more magical than a grand expedition if it leaves behind one true sentence.",
        "tags": ["labyrinth-lore", "character", "faculty", "compass-run", "classes"],
    },
    {
        "id": "labyrinth-character-luna-wispwood",
        "sourceID": "labyrinth-lore",
        "title": "Professor Luna Wispwood",
        "prompt": "Follow the class that smells faintly of rain and ink.",
        "body": "Luna Wispwood teaches the tender arts of perception: how a room changes when someone misses home, how weather enters a sentence, how to tell the difference between a silence and an absence. She is beloved by students who feel too much and quietly feared by students who hoped no one would notice.",
        "tags": ["labyrinth-lore", "character", "faculty", "perception", "classes"],
    },
    {
        "id": "labyrinth-character-wellend-thickets",
        "sourceID": "labyrinth-lore",
        "title": "Professor Wellend Thickets",
        "prompt": "Stand still long enough for the path to choose you.",
        "body": "Wellend Thickets teaches paths, thresholds, and the etiquette of not barging through every door. His coat usually carries at least one burr, two folded maps, and a leaf from a tree no one can find twice. He considers getting lost a respectable academic method, provided the student pays attention to what found them there.",
        "tags": ["labyrinth-lore", "character", "faculty", "wayfinding", "thresholds"],
    },
    {
        "id": "labyrinth-character-eleanor-euphony",
        "sourceID": "labyrinth-lore",
        "title": "Professor Eleanor Euphony",
        "prompt": "Hear the spell before it becomes words.",
        "body": "Eleanor Euphony teaches sound as structure: rhyme, resonance, spoken charms, and the way a room can be tuned by one brave sentence. Her students learn that magic does not always glow. Sometimes it harmonizes. Sometimes it waits in the throat until someone gives it breath.",
        "tags": ["labyrinth-lore", "character", "faculty", "sound", "classes"],
    },
    {
        "id": "labyrinth-character-ignatius-imatook",
        "sourceID": "labyrinth-lore",
        "title": "Professor Ignatius Imatook",
        "prompt": "Open the book that refuses to stay shut.",
        "body": "Ignatius Imatook teaches books as living terrain. His lectures involve marginalia that mutters, footnotes with opinions, and volumes that rearrange their indexes when offended. He treats every book as a place with weather, manners, and a door; naturally, his students learn to knock.",
        "tags": ["labyrinth-lore", "character", "faculty", "books", "book-jumping"],
    },
    {
        "id": "labyrinth-character-lydia-boggle",
        "sourceID": "labyrinth-lore",
        "title": "Professor Lydia Boggle",
        "prompt": "Trust the puzzle that makes you laugh first.",
        "body": "Lydia Boggle teaches riddles, misdirection, and the sacred usefulness of nonsense. Her classroom rewards sideways thinking and punishes smugness with extremely educational embarrassment. A Boggle lesson often begins as a game, becomes a puzzle, and ends as a door no one noticed in the wall.",
        "tags": ["labyrinth-lore", "character", "faculty", "riddles", "classes"],
    },
    {
        "id": "labyrinth-character-zara-finch",
        "sourceID": "labyrinth-lore",
        "title": "Zara Finch",
        "prompt": "Meet the student with ink on her sleeve.",
        "body": "Zara Finch is the kind of student who notices the loose thread, the missing comma, and the person pretending not to be lonely. She is quick with a plan and quicker with a correction, though her loyalty is warmer than her first impression suggests. Around Zara, even ordinary errands acquire footnotes.",
        "tags": ["labyrinth-lore", "character", "student", "riddlewind", "academy"],
    },
    {
        "id": "labyrinth-character-wicker-eddies",
        "sourceID": "labyrinth-lore",
        "title": "Wicker Eddies",
        "prompt": "Notice charm used as cover.",
        "body": "Wicker Eddies is polished, popular, and always standing where attention gathers. He can make a cruel remark sound like a compliment if the room is moving fast enough. The Academy keeps students like Wicker in its stories because glamour without kindness is one of the oldest lessons magic has to teach.",
        "tags": ["labyrinth-lore", "character", "student", "academy", "rival"],
    },
    {
        "id": "labyrinth-school-weekly-rhythm",
        "sourceID": "labyrinth-lore",
        "title": "The Academy Week",
        "prompt": "Let the days have different kinds of doors.",
        "body": "A week at the Academy is not a row of identical boxes. Mondays reset the ink. Tuesdays favor practice. Wednesdays go strange in the middle. Thursdays gather consequences. Fridays loosen the rules just enough for clubs, rumors, and chapter business to breathe. Weekends belong to quieter study, unscheduled wonder, and the sort of discovery that happens when no bell rings.",
        "tags": ["labyrinth-lore", "school-life", "schedule", "academy", "classes"],
    },
    {
        "id": "labyrinth-school-daily-blocks",
        "sourceID": "labyrinth-lore",
        "title": "A Day in the Halls",
        "prompt": "Walk the day from breakfast to lamps-out.",
        "body": "Academy days have a practical shape: breakfast warmth, morning classes, a noon hush in the library, afternoon practice, tea-time gossip, evening clubs, and the late hour when corridors seem to remember older footsteps. The schedule is ordinary enough to hold students steady and enchanted enough that no two Tuesdays are entirely the same.",
        "tags": ["labyrinth-lore", "school-life", "schedule", "academy", "daily-life"],
    },
    {
        "id": "labyrinth-class-compass-core",
        "sourceID": "labyrinth-lore",
        "title": "Compass Core",
        "prompt": "Study the four directions of a small adventure.",
        "body": "Compass Core teaches the Academy's most practical ritual: North to Notice, East to Embark, South to Sense, West to Write, and Center to Rest. Students begin with tiny runs because tiny runs are harder to dismiss. A good Compass Core assignment sends a student out with one question, one comfort, one sensory game, and one sentence to bring home.",
        "tags": ["labyrinth-lore", "class", "compass-run", "wonder-compass", "school"],
    },
    {
        "id": "labyrinth-class-art-of-the-glint",
        "sourceID": "labyrinth-lore",
        "title": "Art of the Glint",
        "prompt": "Practice catching the first bright detail.",
        "body": "Art of the Glint is a class about first notice: the shine on a spoon, the odd word in a paragraph, the one green window in a gray street. Students learn that wonder usually arrives small and sideways. The lesson is not to make the world more magical, but to stop walking past the magic already making faces at them.",
        "tags": ["labyrinth-lore", "class", "attention", "wonder", "school"],
    },
    {
        "id": "labyrinth-class-wayfinding",
        "sourceID": "labyrinth-lore",
        "title": "Wayfinding and Narrative Kineticism",
        "prompt": "Learn how motion changes the story.",
        "body": "Wayfinding and Narrative Kineticism studies the relationship between movement and meaning. A corridor walked in grief is not the same corridor walked in curiosity. A path can shorten when named kindly or lengthen when ignored. Students map routes, but they also map the reasons people take them.",
        "tags": ["labyrinth-lore", "class", "wayfinding", "movement", "school"],
    },
    {
        "id": "labyrinth-class-synesthetic-resonance",
        "sourceID": "labyrinth-lore",
        "title": "Synesthetic Resonance",
        "prompt": "Translate one sense into another.",
        "body": "Synesthetic Resonance teaches students to hear colors, taste weather, and notice when a sentence has the texture of velvet or gravel. The class is not about confusion. It is about precision: finding the sensory bridge that lets an experience become vivid enough to remember.",
        "tags": ["labyrinth-lore", "class", "senses", "writing", "school"],
    },
    {
        "id": "labyrinth-class-ink-binding",
        "sourceID": "labyrinth-lore",
        "title": "Ink-Binding",
        "prompt": "Learn why writing something down changes it.",
        "body": "Ink-Binding is the study of promises, souvenirs, field notes, marginalia, and spells that become stronger because they have been written. Students practice small bindings first: a remembered smell, a found phrase, a promise to return. The class teaches that a sentence can be a clasp, a key, or a candle.",
        "tags": ["labyrinth-lore", "class", "writing", "memory", "school"],
    },
    {
        "id": "labyrinth-class-quiet-hours",
        "sourceID": "labyrinth-lore",
        "title": "Quiet Hours",
        "prompt": "Practice rest as a real subject.",
        "body": "Quiet Hours is not a punishment and not a study hall. It is the Academy's formal recognition that magic curdles when every moment is forced to perform. Students sit, mend, read, nap, stare out windows, or listen to rain with academic seriousness. Rest is treated as the center that lets every compass needle return.",
        "tags": ["labyrinth-lore", "class", "rest", "school-life", "academy"],
    },
    {
        "id": "labyrinth-club-compass-society",
        "sourceID": "labyrinth-lore",
        "title": "The Compass Society",
        "prompt": "Join the students who make errands legendary.",
        "body": "The Compass Society is for students who believe an afternoon can become an expedition without becoming dramatic. They trade run ideas, test impossible definitions of 'nearby,' compare one-sentence souvenirs, and keep a wall map full of pins that mark tiny brave departures: bakery loops, rainy walks, new benches, unfamiliar aisles.",
        "tags": ["labyrinth-lore", "club", "compass-run", "students", "academy"],
    },
    {
        "id": "labyrinth-club-marginalia-guild",
        "sourceID": "labyrinth-lore",
        "title": "The Marginalia Guild",
        "prompt": "Write in the edge where the book can hear you.",
        "body": "The Marginalia Guild gathers students who cannot leave a page alone. They annotate recipes, prophecies, maps, detention notices, and each other's terrible drafts. Their unofficial motto is that the margin is where a reader becomes a co-conspirator. The Library tolerates them because some of their notes have saved entire shelves.",
        "tags": ["labyrinth-lore", "club", "books", "writing", "students"],
    },
    {
        "id": "labyrinth-club-inkwright-society",
        "sourceID": "labyrinth-lore",
        "title": "The Inkwright Society",
        "prompt": "Build the page that can hold the spell.",
        "body": "The Inkwright Society studies physical making: paper, binding, nibs, seals, pigments, repairs, and the stubborn craft of keeping magic legible. Members care about the hinge of a book, the weight of a card, and whether a label will survive a pocket. They make artifacts that feel as if they were always waiting to be found.",
        "tags": ["labyrinth-lore", "club", "craft", "books", "students"],
    },
    {
        "id": "labyrinth-club-book-jumpers",
        "sourceID": "labyrinth-lore",
        "title": "The Book Jumpers",
        "prompt": "Step carefully into a borrowed story.",
        "body": "The Book Jumpers are equal parts literary society, expedition club, and emergency retrieval team. They study how to enter a story without trampling it, how to bring back only what belongs to memory, and how to recognize when a narrative is thinning. Their best members are brave, polite, and very good at leaving before the plot notices too much.",
        "tags": ["labyrinth-lore", "club", "book-jumping", "books", "students"],
    },
    {
        "id": "labyrinth-club-still-club",
        "sourceID": "labyrinth-lore",
        "title": "Still Club",
        "prompt": "Find the club that does almost nothing on purpose.",
        "body": "Still Club meets for tea, mending, cloud-watching, listening, and the radical act of not improving the moment. It is beloved by exhausted students and misunderstood by ambitious ones. The club's quiet belief is that attention does not always have to move outward. Sometimes the most magical fieldwork is staying gently where you are.",
        "tags": ["labyrinth-lore", "club", "rest", "students", "academy"],
    },
    {
        "id": "labyrinth-chapter-emberheart",
        "sourceID": "labyrinth-lore",
        "title": "Emberheart Chapter",
        "prompt": "Follow the chapter that keeps the fire useful.",
        "body": "Emberheart is the chapter of warmth, daring, craft, and brave beginnings. Its students are not simply bold; at their best, they are kindling for other people's courage. Emberheart magic favors lamps, hearths, sparks, kitchens, rescue, and the decisive moment when a person says yes before fear has finished making its case.",
        "tags": ["labyrinth-lore", "chapter", "emberheart", "students", "talisman"],
    },
    {
        "id": "labyrinth-chapter-mossbloom",
        "sourceID": "labyrinth-lore",
        "title": "Mossbloom Chapter",
        "prompt": "Look for the chapter that grows quietly.",
        "body": "Mossbloom is the chapter of patience, repair, rooting, and green persistence. Its students understand that not every victory looks like a blaze; some look like a seedling returning after winter. Mossbloom magic favors gardens, mending, slow courage, careful care, and the kind of strength that makes a shelter instead of a spectacle.",
        "tags": ["labyrinth-lore", "chapter", "mossbloom", "students", "talisman"],
    },
    {
        "id": "labyrinth-chapter-tidecrest",
        "sourceID": "labyrinth-lore",
        "title": "Tidecrest Chapter",
        "prompt": "Stand where feeling and weather meet.",
        "body": "Tidecrest is the chapter of feeling, memory, music, water, and change. Its students are often accused of being dramatic by people who mistake depth for inconvenience. Tidecrest magic favors shorelines, rain, songs, letters, dreams, and the difficult grace of letting an emotion move without letting it drown the room.",
        "tags": ["labyrinth-lore", "chapter", "tidecrest", "students", "talisman"],
    },
    {
        "id": "labyrinth-chapter-riddlewind",
        "sourceID": "labyrinth-lore",
        "title": "Riddlewind Chapter",
        "prompt": "Catch the answer that arrives disguised as a question.",
        "body": "Riddlewind is the chapter of wit, puzzles, language, maps, and unexpected routes. Its students love locked boxes, unsolved footnotes, and jokes that secretly contain instructions. Riddlewind magic favors ciphers, breezes, questions, marginalia, and the sideways step that makes a wall admit it was a door.",
        "tags": ["labyrinth-lore", "chapter", "riddlewind", "students", "talisman"],
    },
    {
        "id": "labyrinth-chapter-duskthorn",
        "sourceID": "labyrinth-lore",
        "title": "Duskthorn Chapter",
        "prompt": "Read the rumor, then leave room for shadow.",
        "body": "Duskthorn is spoken of as a hidden or half-remembered chapter: twilight, thorns, secrecy, difficult protection, and the costs of guarding what others would rather not name. Some students insist it is only a story told to make the chapter system feel complete. Others lower their voices when the west windows go violet.",
        "tags": ["labyrinth-lore", "chapter", "duskthorn", "rumor", "talisman"],
    },
    {
        "id": "labyrinth-talisman-ember-seal",
        "sourceID": "labyrinth-lore",
        "title": "The Ember Seal",
        "prompt": "Hold the mark of a useful flame.",
        "body": "The Ember Seal is associated with Emberheart's oath to warm, illuminate, and begin. It is imagined as a small heat that does not burn the palm: a reminder that courage is meant to be carried into kitchens, sickrooms, cold walks, and first attempts, not saved for theatrical emergencies.",
        "tags": ["labyrinth-lore", "talisman", "emberheart", "chapter", "artifact"],
    },
    {
        "id": "labyrinth-talisman-moss-clasp",
        "sourceID": "labyrinth-lore",
        "title": "The Moss Clasp",
        "prompt": "Fasten yourself to what keeps growing.",
        "body": "The Moss Clasp belongs to Mossbloom's slow magic. It suggests repair, shelter, rootwork, and the quiet bravery of returning. A student who imagines the clasp correctly does not picture a trophy. They picture something that holds: a repaired strap, a garden gate, a hand around a mug, a promise kept gently.",
        "tags": ["labyrinth-lore", "talisman", "mossbloom", "chapter", "artifact"],
    },
    {
        "id": "labyrinth-talisman-tide-glass",
        "sourceID": "labyrinth-lore",
        "title": "The Tide Glass",
        "prompt": "Look through the lens that remembers water.",
        "body": "The Tide Glass is Tidecrest's talisman of feeling made visible. It is not for predicting moods or controlling them. It is for noticing the shape of a wave before it breaks, the salt left after tears, the shimmer that proves something moved through you and did not leave you empty.",
        "tags": ["labyrinth-lore", "talisman", "tidecrest", "chapter", "artifact"],
    },
    {
        "id": "labyrinth-talisman-wind-cipher",
        "sourceID": "labyrinth-lore",
        "title": "The Wind Cipher",
        "prompt": "Turn the answer until it catches air.",
        "body": "The Wind Cipher is Riddlewind's talisman of moving thought. It belongs to clues, questions, jokes, maps, and the bright moment when a stuck idea suddenly has another side. Students say it is less like possessing an answer than carrying a small weather system for the mind.",
        "tags": ["labyrinth-lore", "talisman", "riddlewind", "chapter", "artifact"],
    },
    {
        "id": "labyrinth-talisman-dusk-thorn",
        "sourceID": "labyrinth-lore",
        "title": "The Dusk Thorn",
        "prompt": "Respect the symbol that protects by pricking.",
        "body": "The Dusk Thorn is the rumored sign of Duskthorn: a talisman of boundaries, secrecy, and hard protection. It is not cruel, though it is rarely comfortable. A thorn says that beauty may defend itself, that twilight still belongs to the day, and that some doors stay closed for merciful reasons.",
        "tags": ["labyrinth-lore", "talisman", "duskthorn", "chapter", "artifact"],
    },
    {
        "id": "labyrinth-system-enchantments",
        "sourceID": "labyrinth-lore",
        "title": "Enchantments",
        "prompt": "Use attention as a spell.",
        "body": "Enchantments are pen-spells aimed at the real world. A photographed object, room, pet, meal, plant, or strange little corner becomes the focus of magic: it may speak, turn poetic, reveal a hidden story, become wonderful, or show its secret correspondences. The spell works because the player truly looks. The pen focuses the attention; the world supplies the wonder.",
        "tags": ["labyrinth-lore", "system", "enchantment", "magic", "real-world"],
    },
    {
        "id": "labyrinth-system-compass-runs",
        "sourceID": "labyrinth-lore",
        "title": "Compass Runs",
        "prompt": "Make a complete loop through wonder.",
        "body": "A Compass Run is a guided little adventure through five stations: North asks an I-wonder question, East makes a tiny plan, South gives the senses a playful mission, West captures one true sentence, and Center lets the whole thing rest. The size does not matter. A kitchen, a porch, a city block, or a day trip can all become a Run if the loop is complete.",
        "tags": ["labyrinth-lore", "system", "compass-run", "wonder-compass", "real-world"],
    },
    {
        "id": "labyrinth-system-book-jumping",
        "sourceID": "labyrinth-lore",
        "title": "Book Jumping",
        "prompt": "Enter the story without bruising it.",
        "body": "Book Jumping is the art of stepping into a text as if it were terrain. A jumper treats characters as people, settings as weathered rooms, and plot as a current that should be read before it is crossed. The best jumpers bring back insight rather than souvenirs, because a borrowed story is not a shop. It is a place that trusted you briefly.",
        "tags": ["labyrinth-lore", "system", "book-jumping", "books", "stories"],
    },
    {
        "id": "labyrinth-system-belief",
        "sourceID": "labyrinth-lore",
        "title": "Belief",
        "prompt": "Measure how vivid the world feels.",
        "body": "Belief is the Academy's name for the energy created when attention, courage, and meaning gather in one place. High Belief makes the ink dark, the colors sharp, and the impossible feel cooperative. Low Belief does not mean failure. It means the world has gone muted and needs small, concrete acts of noticing to brighten again.",
        "tags": ["labyrinth-lore", "system", "belief", "magic", "attention"],
    },
    {
        "id": "labyrinth-system-the-nothing",
        "sourceID": "labyrinth-lore",
        "title": "The Nothing",
        "prompt": "Name the force that makes everything less.",
        "body": "The Nothing is not a monster with a speech. It is erasure: colors dulling, details vanishing, stories flattening, rooms becoming merely rooms. It feeds on inattention and routine until the world feels like a summary of itself. Enchantments and Compass Runs oppose it because they make specific, sensory meaning in the real world.",
        "tags": ["labyrinth-lore", "system", "nothing", "attention", "wonder"],
    },
    {
        "id": "labyrinth-system-anchor-rooms",
        "sourceID": "labyrinth-lore",
        "title": "Anchor Rooms",
        "prompt": "Let a real place answer in Academy terms.",
        "body": "Some real-world places become Anchor Rooms in the Outer Stacks. They remain exactly what they are, but the Labyrinth learns their room-feeling: a market becomes a bazaar of bargains, a pier becomes a tidal classroom, a familiar cafe becomes a small warm kingdom. An Anchor Room does not replace the place. It gives the place another way to be read.",
        "tags": ["labyrinth-lore", "system", "outer-stacks", "anchors", "location"],
    },
    {
        "id": "labyrinth-system-chapter-binding",
        "sourceID": "labyrinth-lore",
        "title": "Chapter Binding",
        "prompt": "Understand belonging as a living bookmark.",
        "body": "A Chapter is not only a house color or a dormitory banner. It is a pattern of attention: what a student notices first, what kind of courage they practice, what sort of wonder keeps finding them. Chapter Binding is the slow recognition that a person and a tradition have begun reading each other.",
        "tags": ["labyrinth-lore", "system", "chapters", "talisman", "academy"],
    },
]

REAL_WORLD_LORE_SNIPPETS = [
    {
        "id": "real-lore-brownie-hearth",
        "sourceID": "labyrinth-lore",
        "title": "Brownies at the Hearth",
        "prompt": "Notice the house-helping kind of magic.",
        "body": "In Scottish and northern English folklore, brownies are household spirits associated with quiet labor: sweeping, churning, tidying, watching the threshold. They are often rewarded with milk, cream, or a small portion of food, but stories warn that formal payment or disrespect may drive them away. The brownie is a good Lore Page because it treats domestic care as enchanted without making it grand.",
        "tags": ["real-world-lore", "faerie", "household", "scotland", "hearth"],
    },
    {
        "id": "real-lore-irish-sidhe",
        "sourceID": "labyrinth-lore",
        "title": "Aos Si and the Hollow Hills",
        "prompt": "Let the hill keep its own door.",
        "body": "Irish tradition often places the Aos Si, the people of the mounds, in an overlapping world reached through old hills, raths, and liminal places. They are not tiny decorative fairies; they are neighbors with protocols, memory, pride, and danger. The safest stories approach them with courtesy, restraint, and the understanding that not every door should be opened.",
        "tags": ["real-world-lore", "faerie", "irish", "sidhe", "threshold"],
    },
    {
        "id": "real-lore-changeling",
        "sourceID": "labyrinth-lore",
        "title": "Changeling Stories",
        "prompt": "Read the old fear under the tale.",
        "body": "Changeling legends appear across Europe and often tell of a fairy child or enchanted substitute left in place of a human infant. Modern readers can hold these stories carefully: they encode fear around illness, disability, postpartum danger, poverty, and unexplained change. A humane Lore Page keeps the uncanny atmosphere while remembering the real families underneath the tale.",
        "tags": ["real-world-lore", "faerie", "family", "caution", "europe"],
    },
    {
        "id": "real-lore-fairy-rings",
        "sourceID": "labyrinth-lore",
        "title": "Fairy Rings",
        "prompt": "Circle the strange without stepping in.",
        "body": "Fairy rings, circles of mushrooms or unusually lush grass, have been explained in folklore as dancing places of fairies, elves, or other hidden folk. Natural science gives the mycelium its own marvel; folklore gives the circle a rule. Do not rush across every boundary. Some patterns ask first to be noticed from the edge.",
        "tags": ["real-world-lore", "faerie", "mushrooms", "threshold", "nature"],
    },
    {
        "id": "real-lore-rowan-red-thread",
        "sourceID": "labyrinth-lore",
        "title": "Rowan and Red Thread",
        "prompt": "Let protection be small and handmade.",
        "body": "Rowan appears often in British and Irish protective folklore. Twigs, berries, or crosses bound with red thread were used as household or livestock charms, especially against ill-wishing and fairy interference. The charm is modest: a twig, a knot, a color. That modesty is part of its power.",
        "tags": ["real-world-lore", "witchcraft", "protection", "rowan", "charm"],
    },
    {
        "id": "real-lore-iron",
        "sourceID": "labyrinth-lore",
        "title": "Cold Iron",
        "prompt": "Remember the metal at the threshold.",
        "body": "Iron is a frequent protective substance in European fairy lore. A nail, horseshoe, knife, key, or iron tool might be placed near a cradle, door, or stable to deter unwanted fairy influence. In story terms, iron stands for the worked, ordinary, human world: the tool in the hand, the hinge on the door, the practical thing that refuses glamour.",
        "tags": ["real-world-lore", "faerie", "protection", "iron", "threshold"],
    },
    {
        "id": "real-lore-hawthorn",
        "sourceID": "labyrinth-lore",
        "title": "Hawthorn Trees",
        "prompt": "Give the thorn tree its distance.",
        "body": "Hawthorn has a tangled place in folklore: May blossom, healing, luck, boundary, and warning. Lone hawthorns are sometimes treated as fairy trees, not to be cut casually. The tree is beautiful and barbed at once, which is exactly the kind of truth folklore remembers better than plain instruction does.",
        "tags": ["real-world-lore", "faerie", "tree", "hawthorn", "may"],
    },
    {
        "id": "real-lore-beltane",
        "sourceID": "labyrinth-lore",
        "title": "Beltane Fires",
        "prompt": "Let the year cross into brightness.",
        "body": "Beltane, traditionally marked around May Day in Gaelic seasonal custom, belongs to fire, fertility, protection, and the summer half of the year. Cattle, households, and people were blessed through flame and smoke in different local practices. It is a threshold festival: winter behind, heat ahead, the world stepping through a bright gate.",
        "tags": ["real-world-lore", "witchcraft", "seasonal", "beltane", "fire"],
    },
    {
        "id": "real-lore-samhain",
        "sourceID": "labyrinth-lore",
        "title": "Samhain and the Thin Place",
        "prompt": "Let the dark half have manners.",
        "body": "Samhain, around the beginning of November in Gaelic seasonal reckoning, is associated with the dark half of the year and with thresholds between the living and the dead. Modern Halloween carries some of its atmosphere, though not as a simple one-to-one survival. A Lore Page can use Samhain as a reminder that endings deserve ritual attention.",
        "tags": ["real-world-lore", "witchcraft", "seasonal", "samhain", "ancestors"],
    },
    {
        "id": "real-lore-cunning-folk",
        "sourceID": "labyrinth-lore",
        "title": "Cunning Folk",
        "prompt": "Honor practical magic with muddy shoes.",
        "body": "Cunning folk in Britain and parts of Europe were local practitioners people consulted for healing, lost goods, counter-magic, love troubles, protection, and everyday uncertainty. They sit in the complicated borderland between religion, medicine, folk custom, and magic. Their work was rarely abstract. It belonged to kitchens, stables, sickbeds, fields, gossip, and need.",
        "tags": ["real-world-lore", "witchcraft", "folk-magic", "cunning-folk", "history"],
    },
    {
        "id": "real-lore-witch-bottle",
        "sourceID": "labyrinth-lore",
        "title": "Witch Bottles",
        "prompt": "Let the hidden bottle guard the wall.",
        "body": "Witch bottles are protective objects found in British folk magic and archaeology: vessels filled with pins, nails, hair, urine, red thread, or other charged materials, then hidden in walls, hearths, thresholds, or earth. They are not decorative magic. They are anxious, practical, defensive, and deeply embodied: a household trying to keep harm outside.",
        "tags": ["real-world-lore", "witchcraft", "protection", "bottle", "household"],
    },
    {
        "id": "real-lore-poppets",
        "sourceID": "labyrinth-lore",
        "title": "Poppets",
        "prompt": "Notice the small body made of symbol.",
        "body": "A poppet is a small human-shaped figure used in folk magic for healing, protection, binding, or harm depending on context and intention. It may be cloth, wax, clay, root, or straw. The important point is correspondence: a small made thing stands for a living body or situation, letting care or fear become touchable.",
        "tags": ["real-world-lore", "witchcraft", "sympathetic-magic", "poppet", "folk-magic"],
    },
    {
        "id": "real-lore-charm-books",
        "sourceID": "labyrinth-lore",
        "title": "Charm Books and Receipt Books",
        "prompt": "Let the notebook be a working object.",
        "body": "Before magic was neatly separated from medicine, cooking, prayer, and household management, charms often lived in notebooks beside recipes and remedies. A receipt book might hold a cough syrup, a cake, an ink recipe, and a spoken charm in neighboring pages. This is useful lore for ReEnchanted because it treats the page itself as a practical tool.",
        "tags": ["real-world-lore", "witchcraft", "books", "charms", "household"],
    },
    {
        "id": "real-lore-grimoires",
        "sourceID": "labyrinth-lore",
        "title": "Grimoires",
        "prompt": "Respect the book that claims to work.",
        "body": "Grimoires are books of ritual instruction, spirit catalogues, prayers, seals, planetary timing, and ceremonial procedures. Famous examples circulated through copying, translation, secrecy, and print. They are not all one tradition, but they share a serious idea: a book can be an instrument, not just a container of information.",
        "tags": ["real-world-lore", "witchcraft", "books", "ritual", "history"],
    },
    {
        "id": "real-lore-mandrake",
        "sourceID": "labyrinth-lore",
        "title": "Mandrake Root",
        "prompt": "Let the root look back.",
        "body": "Mandrake became famous in European magical and medical lore because its forked root can resemble a human body. Stories gathered around its danger, harvest, sleep, fertility, and uncanny vitality. The mandrake is a reminder that resemblance matters in sympathetic magic: the world keeps making shapes that invite interpretation.",
        "tags": ["real-world-lore", "witchcraft", "plants", "mandrake", "sympathetic-magic"],
    },
    {
        "id": "real-lore-elder",
        "sourceID": "labyrinth-lore",
        "title": "Elder Tree Manners",
        "prompt": "Ask before cutting the old wood.",
        "body": "Elder trees carry strong folklore across Europe: healing flowers and berries, protective associations, and warnings against careless cutting. In some traditions, one asks permission before taking elder wood. Whether read as spirit etiquette or ecological courtesy, the lesson is elegant: do not treat living materials as inert.",
        "tags": ["real-world-lore", "witchcraft", "plants", "elder", "etiquette"],
    },
    {
        "id": "real-lore-liminal-times",
        "sourceID": "labyrinth-lore",
        "title": "Liminal Times",
        "prompt": "Watch the hinge of the day.",
        "body": "Folklore loves hinge-times: dawn, dusk, midnight, noon, New Year's, May Eve, Halloween, the moment before a journey, the breath before a door opens. These times are neither one thing nor the other, and therefore more available to story. A Lore Page can use liminality without drama: the kettle clicks off, the room changes key.",
        "tags": ["real-world-lore", "folklore", "threshold", "time", "liminal"],
    },
    {
        "id": "real-lore-crossroads",
        "sourceID": "labyrinth-lore",
        "title": "Crossroads",
        "prompt": "Stand where choices have worn the ground.",
        "body": "Crossroads appear in many folk traditions as places of meeting, burial, bargain, divination, danger, and decision. They are practical geography made symbolic by repetition: people pass, hesitate, trade news, choose direction. The crossroads does not have to glow. Its power is that several futures touch the same patch of ground.",
        "tags": ["real-world-lore", "folklore", "threshold", "crossroads", "choice"],
    },
    {
        "id": "real-lore-wells",
        "sourceID": "labyrinth-lore",
        "title": "Holy Wells and Wishing Wells",
        "prompt": "Let water remember the offering.",
        "body": "Wells and springs are old centers of healing, pilgrimage, offering, and divination. Coins, pins, cloth strips, prayers, and visits accumulate around water that comes from below. A well is a natural archive: depth, reflection, thirst, cure, and wish all gathered in one dark mouth.",
        "tags": ["real-world-lore", "folklore", "water", "wells", "healing"],
    },
    {
        "id": "real-lore-selkies",
        "sourceID": "labyrinth-lore",
        "title": "Selkie Skins",
        "prompt": "Do not steal what lets someone return to themselves.",
        "body": "Selkie stories from Scottish, Irish, Faroese, and northern island traditions often tell of seal-people who remove their skins to become human. When a human hides the skin, the selkie is trapped. The tale is beautiful and devastating because the skin is not clothing. It is agency, home, and the right to leave.",
        "tags": ["real-world-lore", "faerie", "selkie", "sea", "agency"],
    },
    {
        "id": "real-lore-kelpie",
        "sourceID": "labyrinth-lore",
        "title": "Kelpies",
        "prompt": "Let the water horse keep its warning.",
        "body": "The kelpie of Scottish folklore is often a dangerous water horse, lovely or useful until it pulls the unwary into lochs and rivers. Like many water spirits, it teaches respect for beauty that can kill. A modern Lore Page need not make the kelpie a monster; it can make the river legible as power.",
        "tags": ["real-world-lore", "faerie", "kelpie", "water", "scotland"],
    },
    {
        "id": "real-lore-wild-hunt",
        "sourceID": "labyrinth-lore",
        "title": "The Wild Hunt",
        "prompt": "Hear the riders before the storm breaks.",
        "body": "The Wild Hunt appears in northern and western European folklore as a spectral procession of riders, hounds, the dead, or uncanny hunters crossing the sky or land. It is weather, memory, dread, and old authority moving too fast to stop. The sensible response is not heroism. It is shelter, respect, and listening.",
        "tags": ["real-world-lore", "folklore", "wild-hunt", "winter", "storm"],
    },
    {
        "id": "real-lore-household-wards",
        "sourceID": "labyrinth-lore",
        "title": "Household Wards",
        "prompt": "Find the small defenses already near the door.",
        "body": "Household protection in folk practice often uses ordinary materials: salt, iron, pins, brooms, shoes in walls, marks near doors, herbs over lintels, or spoken blessings. These practices make a house feel like a participant in safety. The ward is not spectacle. It is the home saying, in objects, stay well.",
        "tags": ["real-world-lore", "witchcraft", "protection", "household", "wards"],
    },
    {
        "id": "real-lore-divination",
        "sourceID": "labyrinth-lore",
        "title": "Small Divinations",
        "prompt": "Ask the pattern, then stay responsible.",
        "body": "Folk divination ranges from cards and lots to dreams, wax, water, fire, birds, books, and household accidents. Its best use is not surrendering choice to signs. It is making attention sharper: what did the pattern stir, what question became clearer, what truth did the person already half-know?",
        "tags": ["real-world-lore", "witchcraft", "divination", "attention", "pattern"],
    },
    {
        "id": "real-lore-milk-for-fairies",
        "sourceID": "labyrinth-lore",
        "title": "Milk Left Out",
        "prompt": "Let hospitality have boundaries.",
        "body": "Milk, cream, butter, bread, and small portions of food appear often in fairy and household-spirit lore as offerings. The gesture matters: acknowledgment without ownership, hospitality without a demand. But folklore also knows boundaries. Feeding the unseen does not mean inviting it to rule the house.",
        "tags": ["real-world-lore", "faerie", "offerings", "household", "hospitality"],
    },
]

def clean_markdown(text: str) -> str:
    text = text.replace("\f", "\n")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.M)
    text = re.sub(r"[*_`>#]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def first_heading(text: str, fallback: str) -> str:
    markdown_heading = None
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if stripped.startswith("#") and markdown_heading is None:
            markdown_heading = stripped.lstrip("#").strip()
        if lowered.startswith("chapter "):
            return stripped
    if markdown_heading:
        return markdown_heading
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("part "):
            return stripped
    return fallback


def clean_paragraphs(text: str) -> list[str]:
    cleaned = clean_markdown(text)
    return [
        paragraph.strip()
        for paragraph in cleaned.split("\n\n")
        if len(paragraph.strip()) > 80 and not paragraph.strip().startswith("Chapter ")
    ]


def excerpt(text: str, limit: int = 640) -> str:
    paragraphs = clean_paragraphs(text)
    body = paragraphs[0] if paragraphs else cleaned
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) <= limit:
        return body
    clipped = body[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def plain_text(value: object, limit: int = 420) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = clean_markdown(text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def slugify(value: str) -> str:
    text = re.sub(r"[“”\"'’]", "", value.lower())
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "character"


def pascal_slug(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("-") if part)


def clipped_excerpt(text: str, limit: int = 1_150) -> str:
    body = re.sub(r"\s+", " ", text).strip()
    if len(body) <= limit:
        return body
    clipped = body[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def chapter_sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem.lower()
    if stem == "read-this-first":
        return (0, stem)
    if stem == "introduction":
        return (1, stem)
    match = re.match(r"chapter(\d+)([a-z]?)$", stem)
    if match:
        chapter_number = int(match.group(1))
        suffix = match.group(2)
        suffix_offset = ord(suffix) - ord("a") if suffix else -1
        return (chapter_number * 10 + 10 + suffix_offset, stem)
    return (10_000, stem)


def normalize_toc_title(title: str) -> str:
    title = clean_markdown(title)
    title = re.sub(r"^\s*#+\s*", "", title).strip()
    return title.rstrip(".")


def toc_slug_for_title(title: str) -> str | None:
    lowered = normalize_toc_title(title).lower()
    if lowered.startswith("read this first"):
        return "read-this-first"
    if lowered.startswith("introduction"):
        return "introduction"
    match = re.match(r"chapter\s+(\d+)\s*([a-z]?)\b", lowered)
    if not match:
        return None
    return f"chapter{int(match.group(1))}{match.group(2)}"


def wonder_toc_entries() -> list[dict[str, str]]:
    toc_path = WONDER_DIR / "BOOK_TOC.md"
    if not toc_path.exists():
        return []

    entries: list[dict[str, str]] = []
    pending: dict[str, str] | None = None
    for line in toc_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        bold = re.fullmatch(r"\*\*(.+?)\*\*", stripped)
        if bold:
            title = normalize_toc_title(bold.group(1))
            slug = toc_slug_for_title(title)
            if slug:
                pending = {"slug": slug, "title": title, "summary": ""}
                entries.append(pending)
            else:
                pending = None
            continue
        if pending and not pending["summary"] and not stripped.startswith("#") and not stripped.startswith("-"):
            pending["summary"] = clean_markdown(stripped)
            pending = None
    return entries


def full_chapter_body(raw: str) -> str:
    cleaned = clean_markdown(raw)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def tags_for_text(source: str, text: str) -> list[str]:
    lowered = text.lower()
    tags = [source]
    keywords = {
        "notice": ["notice", "noticing", "attention", "glint"],
        "embark": ["embark", "adventure", "threshold", "walk"],
        "sense": ["sense", "sensory", "sound", "texture", "body"],
        "write": ["write", "sentence", "souvenir", "memory"],
        "rest": ["rest", "center", "gentle", "tired"],
        "belief": ["belief", "narrative weight", "lifeblood"],
        "characters": ["character", "npc", "professor", "student"],
        "relationships": ["relationship", "gossip", "trust"],
        "outer-stacks": ["outer stacks", "location", "anchor"],
        "nothing": ["nothing", "duskthorn", "unwritten"],
    }
    for tag, needles in keywords.items():
        if any(needle in lowered for needle in needles):
            tags.append(tag)
    return sorted(set(tags))


def prompt_for_wonder(title: str, body: str) -> str:
    lowered = f"{title} {body}".lower()
    if "rest" in lowered or "fatigue" in lowered or "dark" in lowered:
        return "Let the Compass get smaller."
    if "write" in lowered or "souvenir" in lowered:
        return "Keep one sentence before the day blurs."
    if "sense" in lowered or "texture" in lowered or "sound" in lowered:
        return "Give one sense a tiny mission."
    if "embark" in lowered or "adventure" in lowered:
        return "Cross one tiny threshold."
    if "notice" in lowered or "attention" in lowered:
        return "Notice one thing your brain tried to skip."
    return "Try one small Compass loop."


def prompt_for_lore(title: str, body: str) -> str:
    lowered = f"{title} {body}".lower()
    if "character" in lowered or "professor" in lowered or "npc" in lowered:
        return "Let a character tug the margin."
    if "belief" in lowered:
        return "Notice what has narrative weight."
    if "outer stacks" in lowered or "location" in lowered:
        return "Let place become story logic."
    if "nothing" in lowered:
        return "Name the pressure without feeding it."
    return "Let the lore brush against today."


def character_prompt(name: str, profile: dict[str, object]) -> str:
    core = plain_text(profile.get("core"), limit=520)
    signature = plain_text(profile.get("signature"), limit=180)
    palette = plain_text(profile.get("palette"), limit=160)
    silhouette = plain_text(profile.get("silhouette"), limit=180)
    continuity = plain_text(profile.get("continuity"), limit=220)
    marginalia = "; ".join(character_marginalia(name, profile))
    return (
        "Create an Enchantify Academy character dossier illustration in the uploaded reference style: "
        "antique parchment collage, central sparse graphite-and-ink portrait, delicate crosshatching, warm sepia paper, "
        "transparent watercolor washes, restrained shadows, and small pops of jewel-like color from the character palette. "
        "Build the margins from character-specific scraps: taped field notes, an academy stamp, small compass marks, "
        "botanical or symbolic marginalia, handwritten annotations, weathered edges, subtle ink stains, and a miniature inset portrait or evidence scrap. "
        f"Character: {name}. Canon visual profile: {core}. Signature object: {signature}. "
        f"Palette: {palette}. Silhouette and pose: {silhouette}. Continuity rule: {continuity}. "
        f"Marginalia should reference: {marginalia}. "
        "Keep the character as the first read, with the academy-file scraps supporting the portrait."
    )


def character_negative_prompt(profile: dict[str, object]) -> str:
    avoid = plain_text(profile.get("avoid"), limit=320)
    base = (
        "Do not make a generic fantasy pinup, shiny digital concept art, glossy anime, plastic skin, "
        "photo-real celebrity likeness, modern office portrait, cluttered room-first scene, illegible face, "
        "heavy oil paint, neon glow, thick airbrush rendering, overfull collage, or inconsistent signature object."
    )
    return f"{base} Avoid: {avoid}" if avoid else base


def character_marginalia(name: str, profile: dict[str, object]) -> list[str]:
    chapter = plain_text(profile.get("chapter"), limit=80)
    signature = plain_text(profile.get("signature"), limit=120)
    palette = plain_text(profile.get("palette"), limit=120)
    core = plain_text(profile.get("core"), limit=220)
    notes = [
        f"file tab labeled {name}",
        f"signature evidence: {signature}" if signature else "signature evidence",
        f"jewel-color swatches: {palette}" if palette else "jewel-color swatches",
    ]
    if chapter:
        notes.append(f"chapter mark: {chapter}")
    if core:
        notes.append(f"one short handwritten note from the canon profile: {core}")
    return notes


def character_tags(name: str, profile: dict[str, object]) -> list[str]:
    tags = ["character", "illustration", slugify(name)]
    chapter = profile.get("chapter")
    status = profile.get("status")
    if chapter:
        tags.append(slugify(str(chapter)))
    if status:
        tags.append(slugify(str(status)))
    return sorted(set(tags))


def character_illustration_profiles() -> list[dict[str, object]]:
    if not CHARACTER_VISUALS.exists():
        return []

    raw = json.loads(CHARACTER_VISUALS.read_text(encoding="utf-8"))
    characters = raw.get("characters") or {}
    profiles: list[dict[str, object]] = []
    for name, profile in characters.items():
        if not isinstance(profile, dict):
            continue
        slug = slugify(name)
        intended_asset_name = f"LabyrinthCharacter{pascal_slug(slug)}"
        profiles.append({
            "id": slug,
            "characterName": name,
            "slug": slug,
            "status": str(profile.get("status") or ""),
            "chapter": profile.get("chapter"),
            "core": plain_text(profile.get("core"), limit=620),
            "signature": plain_text(profile.get("signature"), limit=220),
            "palette": plain_text(profile.get("palette"), limit=220),
            "silhouette": plain_text(profile.get("silhouette"), limit=260),
            "continuity": plain_text(profile.get("continuity"), limit=320),
            "avoid": plain_text(profile.get("avoid"), limit=360),
            "assetName": intended_asset_name,
            "intendedAssetName": intended_asset_name,
            "prompt": character_prompt(name, profile),
            "negativePrompt": character_negative_prompt(profile),
            "marginalia": character_marginalia(name, profile),
            "tags": character_tags(name, profile),
        })
    return profiles


def wonder_files() -> list[Path]:
    files = [path for path in WONDER_DIR.glob("*.md") if path.name != "BOOK_TOC.md"]
    return sorted(files, key=chapter_sort_key)


def snippet(path: Path, source_id: str, prompt_builder) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    title = first_heading(raw, path.stem.replace("-", " ").title())
    body = excerpt(raw)
    return {
        "id": f"{source_id}-{path.stem.lower()}",
        "sourceID": source_id,
        "title": title,
        "prompt": prompt_builder(title, body),
        "body": body,
        "tags": tags_for_text(source_id, f"{title}\n{raw}"),
    }


def wonder_snippets(path: Path) -> list[dict[str, object]]:
    raw = path.read_text(encoding="utf-8")
    title = first_heading(raw, path.stem.replace("-", " ").title())
    paragraphs = clean_paragraphs(raw)
    if not paragraphs:
        body = excerpt(raw, limit=1_150)
        return [{
            "id": f"wonder-compass-{path.stem.lower()}",
            "sourceID": "wonder-compass",
            "title": title,
            "prompt": prompt_for_wonder(title, body),
            "body": body,
            "tags": tags_for_text("wonder-compass", f"{title}\n{raw}"),
        }]

    windows: list[str] = []
    window: list[str] = []
    current_length = 0
    for paragraph in paragraphs:
        normalized = re.sub(r"\s+", " ", paragraph).strip()
        if not normalized:
            continue
        if window and current_length + len(normalized) > 1_250:
            windows.append(" ".join(window))
            window = []
            current_length = 0
        window.append(normalized)
        current_length += len(normalized) + 1
    if window:
        windows.append(" ".join(window))

    chapter_tags = tags_for_text("wonder-compass", f"{title}\n{raw}")
    snippets: list[dict[str, object]] = []
    for index, body in enumerate(windows[:6], start=1):
        passage_title = title if len(windows) == 1 else f"{title} · Passage {index}"
        snippets.append({
            "id": f"wonder-compass-{path.stem.lower()}-p{index}",
            "sourceID": "wonder-compass",
            "title": passage_title,
            "prompt": prompt_for_wonder(title, body),
            "body": clipped_excerpt(body),
            "tags": tags_for_text("wonder-compass", f"{passage_title}\n{body}\n{' '.join(chapter_tags)}"),
        })
    return snippets


def wonder_chapter_snippets() -> list[dict[str, object]]:
    files_by_stem = {path.stem.lower(): path for path in wonder_files()}
    toc_entries = wonder_toc_entries()
    ordered_entries: list[dict[str, str]] = []
    seen: set[str] = set()

    for entry in toc_entries:
        slug = entry["slug"].lower()
        if slug in files_by_stem:
            ordered_entries.append(entry)
            seen.add(slug)

    for path in wonder_files():
        slug = path.stem.lower()
        if slug in seen:
            continue
        raw = path.read_text(encoding="utf-8")
        ordered_entries.append({
            "slug": slug,
            "title": first_heading(raw, path.stem.replace("-", " ").title()),
            "summary": excerpt(raw, limit=360),
        })

    snippets: list[dict[str, object]] = []
    for entry in ordered_entries:
        slug = entry["slug"].lower()
        path = files_by_stem[slug]
        raw = path.read_text(encoding="utf-8")
        title = entry["title"] or first_heading(raw, path.stem.replace("-", " ").title())
        summary = entry.get("summary") or prompt_for_wonder(title, raw)
        body = full_chapter_body(raw)
        snippets.append({
            "id": f"wonder-compass-{slug}",
            "sourceID": "wonder-compass",
            "title": title,
            "prompt": summary,
            "body": body,
            "tags": tags_for_text("wonder-compass", f"{title}\n{summary}\n{raw}"),
            "url": str(path.relative_to(ROOT)),
            "preview": clipped_excerpt(body, limit=900),
        })
    return snippets


def patreon_snippets() -> list[dict[str, object]]:
    fallback = [
        {
            "id": "patreon-clubhouse-free-shelf",
            "sourceID": "patreon-packet",
            "title": "Patreon Clubhouse",
            "prompt": "The free shelf is open.",
            "body": (
                "The Wonder Compass ebook, printable play-sheets, Spark menus, Playful Mission menus, "
                f"and Clubhouse notes live at {PATREON_URL}. The practice is free; the attention is real."
            ),
            "tags": ["patreon", "clubhouse", "wonder-compass", "free"],
        }
    ]

    adapter_path = ROOT / "scripts" / "patreon-adapter.py"
    if not adapter_path.exists():
        return fallback
    try:
        spec = importlib.util.spec_from_file_location("patreon_adapter_for_inside_cover", adapter_path)
        if spec is None or spec.loader is None:
            return fallback
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        status = module.status()
    except Exception:
        return fallback

    if not status.get("connected"):
        return fallback

    campaign = (status.get("campaigns") or [{}])[0]
    attrs = campaign.get("attributes") or {}
    campaign_name = clean_markdown(str(attrs.get("creation_name") or "Real Life, Re-Enchanted"))
    campaign_url = str(attrs.get("url") or PATREON_URL).strip() or PATREON_URL
    posts = status.get("posts") or []
    recent = []
    for post in posts[:6]:
        post_attrs = post.get("attributes") or {}
        title = clean_markdown(str(post_attrs.get("title") or "")).strip()
        published = str(post_attrs.get("published_at") or "")[:10]
        excerpt_text = plain_text(
            post_attrs.get("content")
            or post_attrs.get("teaser_text")
            or post_attrs.get("excerpt")
            or post_attrs.get("post_metadata")
            or ""
        )
        if title:
            recent.append((title, published, excerpt_text))

    if not recent:
        return fallback

    recent_lines = "\n".join(
        f"- {title}" + (f" ({published})" if published else "")
        for title, published, _ in recent[:5]
    )
    body = (
        f"{campaign_name} is the public Clubhouse shelf at {campaign_url}.\n\n"
        f"Recent posts:\n{recent_lines}\n\n"
        "The app keeps private pages local; this card only points to public/shared material."
    )
    snippets = [
        {
            "id": "patreon-current-shelf",
            "sourceID": "patreon-packet",
            "title": campaign_name,
            "prompt": "See what is new in the Clubhouse.",
            "body": body,
            "tags": ["patreon", "clubhouse", "recent-posts", "wonder-compass"],
        }
    ]
    for post in posts[:8]:
        post_attrs = post.get("attributes") or {}
        title = clean_markdown(str(post_attrs.get("title") or "")).strip()
        published = str(post_attrs.get("published_at") or "")[:10]
        raw_url = str(post_attrs.get("url") or "").strip()
        preview = plain_text(
            post_attrs.get("content")
            or post_attrs.get("teaser_text")
            or post_attrs.get("excerpt")
            or post_attrs.get("post_metadata")
            or ""
        )
        if not title:
            continue
        full_url = raw_url if raw_url.startswith("http") else f"https://www.patreon.com{raw_url}"
        snippets.append({
            "id": f"patreon-post-{post.get('id')}",
            "sourceID": "patreon-packet",
            "title": title,
            "prompt": "A Clubhouse post is ready.",
            "body": (
                f"{title}"
                + (f"\nPublished: {published}" if published else "")
                + (f"\nPreview: {preview}" if preview else "")
                + f"\n{full_url}"
            ),
            "tags": ["patreon", "clubhouse", "post"],
            "url": full_url,
            "publishedAt": published,
            "preview": preview,
        })
    return snippets


def existing_payload_section(key: str) -> list[dict[str, object]]:
    if not OUTPUT.exists():
        return []
    try:
        payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except Exception:
        return []
    section = payload.get(key)
    return section if isinstance(section, list) else []


def main() -> None:
    wonder = wonder_chapter_snippets()
    lore = CURATED_ENCHANTIFY_LORE + LABYRINTH_LORE_SNIPPETS + REAL_WORLD_LORE_SNIPPETS
    patreon = patreon_snippets()
    if patreon and patreon[0].get("id") == "patreon-clubhouse-free-shelf":
        patreon = existing_payload_section("patreon") or patreon
    character_illustrations = character_illustration_profiles()
    payload = {
        "version": 1,
        "generatedFrom": {
            "wonderCompass": str(WONDER_DIR.relative_to(ROOT)),
            "enchantifyLore": "curated Labyrinth NPC, class, club, chapter, talisman, system, and real-world folklore lore",
            "patreon": "scripts/patreon-adapter.py status",
            "characterVisuals": str(CHARACTER_VISUALS.relative_to(ROOT)),
        },
        "wonderCompass": wonder,
        "enchantifyLore": lore,
        "patreon": patreon,
        "characterIllustrations": character_illustrations,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    print(f"Wonder Compass snippets: {len(wonder)}")
    print(f"Lore snippets: {len(lore)}")
    print(f"Patreon snippets: {len(patreon)}")
    print(f"Character illustration profiles: {len(character_illustrations)}")


if __name__ == "__main__":
    main()
