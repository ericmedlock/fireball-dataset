# CHECKPOINT - Data Quality & Classification
**Date**: February 9, 2025  
**Status**: Hibernating - Character classification complete, data quality issues identified  
**Session**: PC/NPC Classification + Data Corruption Discovery

---

## COMPLETED WORK

### 1. Character Classification System ✓
- Created `classify_characters.py` with heuristic rules
- **Core Rule**: Class + Race = PC (75-90% confidence)
- Fixed misclassifications: Characters with class+race now correctly marked as PCs
- Reclassified all 1,895 characters

**Final Distribution**:
- **740 PCs** (39.1%, avg 81% confidence)
- **733 Monsters** (38.7%, avg 94% confidence)  
- **417 NPCs** (17.9%, avg 57% confidence) - includes 77 zero-confidence defaults
- **5 Other** (0.3%, 100% confidence) - DM, Map, Environment tokens

### 2. Classification Heuristics Documented ✓
- Created comprehensive `ASSUMPTIONS.md` (11 sections, 300+ lines)
- Documents all preprocessing decisions:
  - Character classification rules (9 rules)
  - HP parsing (handles temp HP, negative HP)
  - Class/race parsing (multiclass, subraces)
  - Damage extraction patterns
  - Spell/attack memorization vs. usage
  - Aggregate calculations
  - Data quality decisions

### 3. Examples Verified ✓
**Previously Misclassified NPCs → Now Correctly PCs**:
- `Faldal Laughingcheeks` - Sorcerer/Custom Lineage, 18 appearances, 1 spell cast → **PC**
- `Freya` - Bard/Dusk, 18 appearances, 2 damage events → **PC**
- `Glendid Tangnefedd, Unbound by Fate` - Paladin/Red Dragon, 11 appearances → **PC**

All have class+race+combat activity = PCs (75% confidence)

---

## DATA CORRUPTION ISSUES IDENTIFIED ⚠️

### Race Field Corruption (CRITICAL)
**Pattern**: Race field contains invalid data, not actual D&D races

**Examples Found**:
1. **Race = Character Name** (133+ cases):
   - `Lily` has race="Lily" (132 appearances)
   - `Lilith` has race="Lilith" (133 appearances)
   - `Echo` has race="Echo" (125 appearances)
   - `Gidget` has race="Gidget" (62 appearances)

2. **Race = Character IDs**:
   - `wcjc3y2d8z` (2 characters)
   - Other alphanumeric hashes likely present

3. **Race = Full Character Names**:
   - `Uturik "Chinchillen" Rathen` (contains quotes, full name)
   - `Veldaken [reflavor as Half elf]` (DM notes)

4. **Race = Descriptive Text**:
   - `Spellcaster - Healer (level 12)` (class info, not race)
   - `Custom Lineage Some Kind of Human but with Darkvision` (too long)
   - `Simic Hybrid (Underwater Adaptation)` (valid but very specific)

**Impact**: 
- Corrupts character aggregates (`most_common_race`)
- Affects PC/NPC classification (Rule 8: race-only characters marked as NPCs)
- Pollutes Tableau race dimension
- ~100-150 characters likely affected

### Other Tables - NOT YET CHECKED
Need to validate for similar corruption:
- ❓ **Spells table**: Check `spell_name` for IDs, hashes, corrupt data
- ❓ **Attacks table**: Check `attack_name` for corruption
- ❓ **Effects table**: Check `effect_name` for corruption
- ❓ **Character names**: May contain IDs or system tokens

---

## FILES CREATED THIS SESSION

### Classification System
- `classify_characters.py` (329 lines)
  - `classify_heuristic()`: 9 rule-based patterns
  - `classify_with_llm()`: LM Studio integration (currently disabled for speed)
  - `classify_character()`: Orchestrator (heuristics only in current version)
  - Modified to skip LLM for speed (all heuristics)

### Validation Scripts
- `validate_race_data.py` (NEW, 248 lines) - **NOT YET RUN**
  - `RaceValidator` class with heuristic + LLM validation
  - Detects: name=race, IDs, quotes, length violations
  - Rules cover 99% cases, LLM for edge cases
  - Ready to test on existing DB

### Documentation
- `ASSUMPTIONS.md` (comprehensive preprocessing documentation)
  - All heuristic rules documented
  - Known limitations listed
  - Change log maintained

### Previous Session Files (Still Valid)
- `load_to_sqlite.py` - ETL pipeline (needs corruption filtering)
- `sqlite_to_hyper.py` - Hyper export (needs re-run after cleaning)
- `postprocess_characters.py` - Aggregate calculation
- `fireball.db` (31 MB) - Contains corrupt data
- `fireball.hyper` (3.1 MB) - Contains corrupt data

---

## CURRENT DATABASE STATE

**File**: `fireball.db` (31 MB, 1 of 45 files loaded)

**Row Counts**:
- 1,895 characters (740 PC, 733 Monster, 417 NPC, 5 Other)
- 825 spells
- 3,179 attacks
- 699 effects
- 3,443 actions
- 61,724 character_snapshots
- 528,276 spell memorizations
- 308,575 attack memorizations

**Known Issues**:
- ✗ Race corruption (~100-150 characters)
- ✗ 392 snapshots with current HP > max HP (acceptable per ASSUMPTIONS.md)
- ✗ 139 unparseable class texts (acceptable per ASSUMPTIONS.md)
- ❓ Spell/attack/effect names not validated yet

---

## IMMEDIATE NEXT STEPS (RESUME HERE)

### Step 1: Complete Data Validation (30 min)
```bash
# Test race validation script
python validate_race_data.py

# Check spell names for corruption
sqlite3 fireball.db ".schema spells"
sqlite3 fireball.db "SELECT spell_name, COUNT(*) FROM spells WHERE LENGTH(spell_name) > 40 OR spell_name GLOB '*[0-9][0-9][0-9]*' GROUP BY spell_name LIMIT 20;"

# Check attack names
sqlite3 fireball.db ".schema attacks"  
sqlite3 fireball.db "SELECT attack_name, COUNT(*) FROM attacks WHERE LENGTH(attack_name) > 40 GROUP BY attack_name LIMIT 20;"

# Check effect names
sqlite3 fireball.db ".schema effects"
sqlite3 fireball.db "SELECT effect_name, COUNT(*) FROM effects WHERE LENGTH(effect_name) > 40 GROUP BY effect_name LIMIT 20;"

# Check character names for system tokens
sqlite3 fireball.db "SELECT name, total_appearances FROM characters WHERE name GLOB '*[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*' OR LENGTH(name) > 50 ORDER BY total_appearances DESC LIMIT 20;"
```

### Step 2: Create Data Quality Filter (1-2 hours)
Create `data_quality_filters.py` with validation for:
- Race field (using `validate_race_data.py` logic)
- Spell names (detect IDs, hashes, overly long names)
- Attack names (similar patterns)
- Effect names (similar patterns)  
- Character names (detect system tokens, IDs)

**Approach**:
- Heuristics for 99% of cases (fast)
- LM Studio for edge cases (use qwen2.5-3b-instruct model)
- Returns: `(is_valid, confidence, reason)`

### Step 3: Update ETL Pipeline (1 hour)
Modify `load_to_sqlite.py`:

```python
# Add after imports
from data_quality_filters import (
    validate_race, validate_spell_name, 
    validate_attack_name, validate_effect_name
)

# In parse functions, add validation:
def parse_character_snapshot(snapshot_data, ...):
    # ... existing parsing ...
    
    # Validate race before storing
    if race:
        is_valid, confidence, reason = validate_race(race, char_name)
        if not is_valid and confidence >= 0.90:
            race = None  # Discard corrupt race data
            # Optional: log to corruption_log.txt

# Similar for spells, attacks, effects
```

### Step 4: Clean Existing Database (30 min)
```bash
# Backup first
cp fireball.db fireball_backup.db

# Run cleaning script
python clean_existing_data.py  # Create this script

# Clean operations:
# 1. NULL out corrupt race values (confidence >= 90%)
# 2. Remove/mark corrupt spells/attacks/effects
# 3. Re-calculate character aggregates
# 4. Re-run classification (some NPCs may become Unknown after race cleaning)
```

### Step 5: Re-export to Hyper (10 min)
```bash
python sqlite_to_hyper.py
# Verify row counts match
# Verify no corrupt data in Hyper
```

### Step 6: Load Remaining 44 Files (2-3 hours)
```bash
# Modify load_to_sqlite.py to loop through all files
# With data quality filters in place, load should be clean
python load_all_files.py  # Create wrapper script
```

---

## TECHNICAL DECISIONS NEEDED

### Question 1: How to Handle Corrupt Data?
**Options**:
A. **Set to NULL** (recommended) - preserves character, invalidates field
B. **Delete entire character** - loses combat data
C. **Mark with flag** - keeps for analysis, can filter

**Recommendation**: Option A (NULL) for race/class/spells. Document in ASSUMPTIONS.md.

### Question 2: Confidence Threshold for Filtering?
**Options**:
- ≥90% confidence = discard (aggressive, cleaner data)
- ≥95% confidence = discard (conservative, keeps edge cases)
- ≥99% confidence = discard (very conservative)

**Recommendation**: Start with 90%, review results, adjust if needed.

### Question 3: LLM Usage Strategy?
**Current**: Classification uses heuristics only (fast but may miss edge cases)
**Options**:
A. Heuristics + LLM for uncertain (slow but accurate)
B. Heuristics only (fast, ~95% accurate)
C. LLM for validation phase only (balanced)

**Recommendation**: Option C - use LLM in data quality validation, not real-time ETL.

---

## LM STUDIO STATUS

**URL**: `http://localhost:1234`  
**Available Models**:
- `qwen/qwen2.5-vl-7b` (vision model, not needed)
- `qwen2.5-3b-instruct` (recommended for validation - fast, accurate)
- `qwen3-4b-dnd` (D&D-specific, could be useful)

**Connectivity**: Verified working (last check: Feb 9, 2025)

---

## COMMAND SHORTCUTS FOR RESUME

```bash
# Quick data quality check
sqlite3 fireball.db "SELECT COUNT(*) FROM characters WHERE name = most_common_race;"

# See classification distribution
sqlite3 fireball.db "SELECT character_type, COUNT(*) FROM characters GROUP BY character_type;"

# Test race validator
python validate_race_data.py

# Review assumptions
cat ASSUMPTIONS.md | grep "Rule"

# Check file sizes
ls -lh fireball.db fireball.hyper

# Re-run classification (if needed)
python classify_characters.py

# Re-export to Hyper (after cleaning)
python sqlite_to_hyper.py
```

---

## SUCCESS CRITERIA FOR NEXT SESSION

- [ ] All tables validated for corruption (race, spell, attack, effect, character names)
- [ ] Data quality filters implemented in ETL pipeline
- [ ] Existing database cleaned (corrupt data NULLed or marked)
- [ ] Clean Hyper file exported
- [ ] Ready to load remaining 44 files with clean data pipeline
- [ ] ASSUMPTIONS.md updated with corruption handling rules

**Estimated Time**: 4-6 hours to complete all validation + cleaning + pipeline updates

---

## NOTES & CONTEXT

### Why Race Corruption Matters
- Affects 417 NPCs (many classified by "race only" rule)
- Pollutes Tableau race dimension (can't filter by real races)
- Misleads analysis (e.g., "Lily" race performance?)
- Breaks joins if race used as foreign key

### Why Classification Required Rework
- Original Rule 7: "class but <20 appearances = NPC" was wrong
- D&D reality: Class+race indicates full character sheet = PC
- Guest players, one-shots, new characters have low appearances
- Combat activity (spell casting, damage) confirms PC status

### Grad School Project Context
- 30-hour scope project
- Tableau dashboards need clean dimensions
- PC vs NPC separation critical for meaningful metrics
- Monster data useful for encounter balance analysis
- Data quality > data volume (clean 1 file > corrupt 45 files)

---

## FILES TO REVIEW ON RESUME

1. **ASSUMPTIONS.md** - All preprocessing rules documented
2. **classify_characters.py** - Character classification logic
3. **validate_race_data.py** - Race validation (not yet run)
4. **load_to_sqlite.py** - ETL pipeline (needs corruption filters added)
5. **sqlite_to_hyper.py** - Export script (ready to use)

---

**Last Command**: `sqlite3 fireball.db "SELECT name, COUNT(*) as cnt FROM spells..."`  
**Next Command**: `sqlite3 fireball.db ".schema spells"` (get column names)  
**Goal**: Complete data corruption analysis across all tables

**Session End**: February 9, 2025 - Hibernating during data quality analysis phase
