# Class Filtering & Archetype Extraction - COMPLETE

**Completed:** February 11, 2026

## Overview

Successfully cleaned the FIREBALL dataset to include only official D&D 5e classes, with proper archetype extraction to separate fields. This ensures clean, consistent data for Tableau dashboards and analysis.

---

## Changes Made

### 1. Class Filtering
**Goal:** Remove non-standard homebrew classes, keeping only official WotC classes + Blood Hunter

**Kept (14 classes):**
- **Core PHB**: Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard
- **Eberron**: Artificer
- **Critical Role**: Blood Hunter (widely used homebrew)

**Removed (13 classes):**
- Witch (148 snapshots)
- Twin (93 snapshots)
- SoulBinder (89 snapshots)
- MagicalGirl (58 snapshots)
- Magister (53 snapshots)
- Warlord (40 snapshots)
- Deathknight (39 snapshots)
- SwordSaint (34 snapshots)
- Yaeger (32 snapshots)
- Gunslinger (28 snapshots)
- Death Knight (12 snapshots)
- Shaman (4 snapshots)
- Gunbreaker (1 snapshot)

**Impact:**
- 631 snapshots removed (1.02% of data)
- 61,093 snapshots retained (98.98% of data)
- All removed classes were low-volume homebrew

---

### 2. Archetype Extraction

**Problem:** Original data had archetypes embedded in class names
- "Champion Fighter 12" (archetype prefix)
- "Druid (Circle of Wildfire) 5" (archetype in parentheses)
- "Sorcerer (Heroic Lineage) 1" (subclass in parentheses)

**Solution:** Split into three fields:
- `class_text`: Original raw string (preserved for reference)
- `class_primary`: Base class only (Fighter, Druid, Sorcerer, etc.)
- `class_archetype`: Subclass/archetype (Champion, Circle of Wildfire, Heroic Lineage)

**Examples:**
```
"Champion Fighter 12"
→ class_primary: "Fighter"
→ class_level: 12
→ class_archetype: "Champion"

"Druid (Circle of Wildfire) 5"
→ class_primary: "Druid"
→ class_level: 5
→ class_archetype: "Circle of Wildfire"

"Sorcerer (Heroic Lineage) 1"
→ class_primary: "Sorcerer"
→ class_level: 1
→ class_archetype: "Heroic Lineage"

"College of Masks Bard 4"
→ class_primary: "Bard"
→ class_level: 4
→ class_archetype: "College of Masks"

"Fighter 12"
→ class_primary: "Fighter"
→ class_level: 12
→ class_archetype: NULL
```

**Benefit:** Now you can:
- Filter by base class in Tableau (always clean: "Fighter", "Druid", etc.)
- Optional deeper analysis by archetype
- Create class comparison dashboards without polluted dimensions

---

## Final Class Distribution

| Class | Snapshots | % of Total |
|-------|-----------|------------|
| Fighter | 4,437 | 7.26% |
| Rogue | 3,190 | 5.22% |
| Wizard | 3,175 | 5.20% |
| Artificer | 2,913 | 4.77% |
| Paladin | 2,877 | 4.71% |
| Cleric | 2,132 | 3.49% |
| Monk | 1,874 | 3.07% |
| Barbarian | 1,867 | 3.06% |
| Sorcerer | 1,698 | 2.78% |
| Warlock | 1,601 | 2.62% |
| Bard | 1,438 | 2.35% |
| Druid | 1,252 | 2.05% |
| Ranger | 1,208 | 1.98% |
| Blood Hunter | 742 | 1.21% |
| **NULL** | 30,689 | 50.23% |

**Note:** 50% of snapshots have NULL class (NPCs, monsters, creatures without classes)

---

## Scripts Updated

### `load_to_sqlite.py`
**Modified:**
- `is_official_class()` - Now filters for 14 official classes
- `parse_class()` - Complete rewrite to extract archetypes:
  - Pattern 1: `"BaseClass (Archetype) Level"`
  - Pattern 2: `"Archetype BaseClass Level"`
  - Pattern 3: `"BaseClass Level"` (no archetype)
- Multiclass handling: Takes first class only
- Bloodhunter variant: Normalized to "Blood Hunter"

**Behavior:**
- Automatically filters during JSON load
- Returns `None` for non-standard classes (snapshot excluded)
- Allows `None` for NPCs/monsters without classes

### `clean_nonstandard_classes.py`
**New script** for post-processing:
- Reparses all existing `class_text` fields
- Extracts archetypes to `class_archetype` field
- Removes snapshots with non-standard classes
- Recalculates character aggregates
- Reports statistics on removed data

**Usage:**
```bash
python clean_nonstandard_classes.py
```

### `sqlite_to_hyper.py`
**No changes needed** - Automatically exports new architecture to Hyper

---

## Database Schema Changes

### `character_snapshots` table
**New column:**
```sql
class_archetype TEXT  -- Subclass/archetype (e.g., "Champion", "Circle of Wildfire")
```

**Modified behavior:**
```sql
class_primary TEXT  -- NOW: Base class only (never "Champion Fighter")
                    -- WAS: Could be compound ("Champion Fighter 12")
```

---

## Verification

### SQLite:
```bash
sqlite3 fireball.db "
SELECT DISTINCT class_primary 
FROM character_snapshots 
WHERE class_primary IS NOT NULL 
ORDER BY class_primary;
"
```
**Output:** 14 classes (Artificer through Wizard + Blood Hunter)

### Hyper:
```python
python verify_hyper_classes.py
```
**Output:** Confirms class filtering and archetype extraction in Hyper file

---

## Impact on Future Loads

When loading remaining 44 JSON files:
- Filtering will be applied automatically during load
- Non-standard classes will be excluded at insertion time
- Archetype extraction will happen during parse
- No post-processing cleanup needed

**Estimated final stats:**
- 14 official classes maintained
- ~98-99% data retention
- Clean class dimensions for Tableau

---

## For Tableau Users

### Clean Filters:
```
Filter by "class_primary" dimension:
- Always 14 consistent values
- No compound names ("Champion Fighter")
- No homebrew classes (Witch, Twin, etc.)
```

### Advanced Analysis:
```
Optional filter by "class_archetype":
- See specific subclass performance
- Compare Champions vs Battle Masters (Fighter)
- Compare Circle of Moon vs Circle of Wildfire (Druid)
```

### Example Dashboards:
1. **Class popularity** - COUNT(DISTINCT character_id) GROUP BY class_primary
2. **Class effectiveness** - AVG(damage) GROUP BY class_primary
3. **Archetype depth** - COUNT(*) WHERE class_archetype IS NOT NULL
4. **Subclass comparison** - Filter Fighter, GROUP BY class_archetype

---

## Files Modified

- `load_to_sqlite.py` - Filtering & parsing logic
- `clean_nonstandard_classes.py` - Post-processing script (NEW)
- `verify_hyper_classes.py` - Verification script (NEW)
- `fireball.db` - Database cleaned & reparsed
- `fireball.hyper` - Regenerated with new data
- `RESUME_HERE.md` - Status updated
- `DATABASE_SUMMARY.md` - Stats updated
- `SCHEMA_GUIDE.md` - Schema documentation updated
- `CLASS_FILTERING_COMPLETE.md` - This file (NEW)

---

## Status: COMPLETE ✓

All files processed, tested, and verified. Ready for Tableau analysis with clean class dimensions.
