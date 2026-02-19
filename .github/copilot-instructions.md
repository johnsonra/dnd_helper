# D&D Helper – Copilot Instructions

## Project Overview
A Streamlit app for D&D 5e play. Currently in the initial build phase — no source files exist yet beyond the `bestiary` submodule. See `prompt.md` for the full feature spec.

## Tech Stack
- **Frontend/app framework:** Streamlit (Python)
- **AI integration:** Google Gemini API (user-supplied API key at runtime)
- **Data source:** `bestiary/` Git submodule — D&D 5e creature data

## Planned Modules
Each feature is a separate Python module:
1. **Character Sheet Generator** – create, save, and edit characters across a campaign
2. **Dice Roller** – d4/d6/d8/d10/d12/d20 with modifiers, advantage/disadvantage, and per-character action buttons
3. **Encounter Builder** – initiative order, HP tracking, Gemini-powered suggestions
4. **Campaign Tracker** – quests, locations, NPCs, events, image/map uploads
5. **Spell/Creature/Item Database** – seeded from `bestiary/`, with Gemini lookup for missing entries

## Bestiary Submodule Structure
`bestiary/_creatures/` contains one Markdown file per creature. Stats are in YAML front matter; abilities are Markdown body text.

Example front matter fields:
```yaml
name: "Aboleth"
tags: [large, aberration, cr10, monster-manual]
str: 21 (+5)
dex: 9 (-1)
con: 15 (+2)
int: 18 (+4)
wis: 15 (+2)
cha: 18 (+4)
size: Large aberration
alignment: lawful evil
challenge: "10 (5,900 XP)"
languages: "..."
senses: "..."
skills: "..."
saving_throws: "..."
speed: "..."
hit_points: "135 (18d10+36)"
armor_class: "17 (natural armor)"
```

`bestiary/_data/creature_types.yml` lists creature type names and their tag slugs.  
`bestiary/_data/challenge_ratings.yml` lists valid CR values.

When importing creatures from the submodule, parse the YAML front matter for structured stats and the Markdown body for ability text.

## Gemini Integration Conventions
- Prompt the user for their Gemini API key on first use; do not hard-code or commit it.
- When fetching a spell, creature, or item from Gemini, send a structured JSON schema so the response can be imported directly into the app's database.
- After receiving Gemini data, always show a confirmation/edit UI before persisting to the database.

## Database
Use a local database (e.g., SQLite) to store characters, campaign data, and any imported spell/creature/item records. The database file should not be committed to the repo.

## Export / Restore
The app must support exporting the full database to flat files and restoring from them. Conventions:
- Export each logical table (characters, campaign, creatures, spells, items, etc.) as a separate JSON file, bundled into a single ZIP archive for download.
- Restore reads a ZIP archive, validates the schema of each file, and upserts records into the database — prompting the user to confirm before overwriting existing data.
- Expose both actions from a dedicated **Settings / Data Management** page in the Streamlit sidebar.
- Exported filenames should include a timestamp (e.g., `dnd_helper_export_20260219_201700.zip`) so backups don't collide.
