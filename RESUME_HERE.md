# PROJECT STATE - Ready to Resume

## WHAT WORKS NOW ✓
- **SQLite Database:** fireball.db (31 MB, 1 of 45 files loaded)
  - 3,443 actions, 1,895 characters, 825 spells
  - 61,093 character snapshots (cleaned, non-standard classes removed)
  - Character aggregates populated (class, race, appearances)
  - Schema includes PC/NPC fields (not yet classified)
  - **Only official D&D 5e classes + Blood Hunter** (14 classes total)
  - **Archetypes properly extracted** to separate `class_archetype` field

- **Hyper Export:** fireball.hyper (1.8 MB)
  - 100% data fidelity from SQLite
  - Ready for Tableau connection
  - 90% smaller due to columnar compression
  - Clean class dimensions for filtering

- **Working Scripts:**
  - `load_to_sqlite.py` - Load JSON → SQLite with auto-aggregation & class filtering
  - `sqlite_to_hyper.py` - SQLite → Hyper export
  - `postprocess_characters.py` - Populate character aggregates
  - `clean_nonstandard_classes.py` - Remove non-official classes & reparse archetypes

## CLASS FILTERING COMPLETE ✓

**Completed:** February 11, 2026

### What Changed:
- **Filtered to official classes only**: 14 classes (Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard, Artificer, Blood Hunter)
- **Removed 13 homebrew classes**: Witch, Twin, SoulBinder, MagicalGirl, Magister, Warlord, Deathknight, SwordSaint, Yaeger, Gunslinger, Death Knight, Shaman, Gunbreaker
- **Data retained**: 98.98% (61,093 of 61,724 snapshots)
- **Archetype extraction**: "Champion Fighter 12" → class=Fighter, level=12, archetype=Champion
- **Pattern support**: "Druid (Circle of Wildfire) 5" → class=Druid, level=5, archetype=Circle of Wildfire

### Current Class Distribution:
- Fighter: 4,437 | Rogue: 3,190 | Wizard: 3,175 | Artificer: 2,913
- Paladin: 2,877 | Cleric: 2,132 | Monk: 1,874 | Barbarian: 1,867
- Sorcerer: 1,698 | Warlock: 1,601 | Bard: 1,438 | Druid: 1,252
- Ranger: 1,208 | Blood Hunter: 742

## NEXT: PC/NPC Classification 🚧
**Status:** Schema ready, classification logic needed

**Resume at:** CHECKPOINT_PC_NPC.md

## THEN: Load Remaining Data 📦
- 44 more JSON files in output/split/
- Estimated: 30-45 min processing 
- Class filtering will be applied automatically during load
- Final size: ~1.4 GB SQLite, ~140 MB Hyper

## FILES
Key scripts: load_to_sqlite.py, sqlite_to_hyper.py
Database: fireball.db
Export: fireball.hyper
Checkpoint: CHECKPOINT_PC_NPC.md
