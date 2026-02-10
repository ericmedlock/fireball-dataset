# Data Processing Assumptions & Heuristics

This document records all assumptions, heuristics, and preprocessing decisions made during ETL and analysis of the FIREBALL D&D combat dataset. These are **interpretive decisions** made where the data required human judgment, not pure collation/summation.

**Last Updated**: February 9, 2025  
**Dataset Version**: FIREBALL v1.0 (45 files, ~2.3GB)

---

## 1. Character Classification Assumptions

### Core Classification Rules

Characters classified into: PC (Player Character), NPC (Non-Player Character), Monster, Other (system tokens), Unknown

#### Rule 1: System/Meta Tokens → Other (100% confidence)
**Names**: `DM`, `dm`, `Map`, `map`, `Environment`, `Player 1-5`  
**Rationale**: These are game system tokens, not actual characters in combat  
**Example**: "DM" with 586 appearances is the Dungeon Master narrator token

#### Rule 2: Coded Monster Names → Monster (95% confidence)
**Pattern**: 2-4 uppercase letters + digit (e.g., `MA1`, `SK2`, `WE1`, `DLoT1`)  
**Rationale**: Avrae bot uses abbreviation codes to track multiple instances of same monster type  
**Examples**: 
- `MA1` = Mage #1 (289 appearances)
- `SK1`, `SK2` = Skeleton #1, #2
- `WE1` = Werewolf #1 (168 appearances)

#### Rule 3: Very Short Uppercase Names → Monster (85% confidence)
**Pattern**: ≤3 characters, all uppercase  
**Rationale**: Abbreviated enemy names (e.g., `ORC`, `GOB`)  
**Limitation**: May misclassify acronym-named PCs

#### Rule 4: Numbered Generic Names → Monster (90% confidence)
**Pattern**: Contains digit + space (e.g., "Goblin 2", "Skeleton 1")  
**Rationale**: Instance numbering used for encounter multiples  
**High confidence** because this pattern is rarely used for player characters

#### Rule 5: **CORE PC RULE - Class + Race → PC (75-90% confidence)**
**Pattern**: Has both `most_common_class` AND `most_common_race` populated  
**CRITICAL ASSUMPTION**: Any character with full class+race data is a playable character with a complete character sheet, not an NPC or monster  
**Rationale**:
- NPCs rarely have detailed class/race tracking in actual play
- If DM tracks class+race+stats, it's a player-controlled character
- Presence in combat encounters with full stats = PC

**Confidence scaling**:
- 50+ appearances: 90% confidence (highly active PC)
- 20-49 appearances: 80% confidence (regular PC)
- 1-19 appearances: 75% confidence (new PC or guest player)

**Examples (previously misclassified)**:
- `Faldal Laughingcheeks` - Sorcerer/Custom Lineage, 18 appearances, 1 spell cast, 1 damage → **PC** (not NPC)
- `Freya` - Bard/Dusk, 18 appearances, 2 damage events → **PC** (not NPC)
- `Glendid Tangnefedd, Unbound by Fate` - Paladin/Red Dragon, 11 appearances, 2 damage → **PC** (not NPC)

#### Rule 6: Class Only (No Race) → PC (70% confidence)
**Pattern**: Has `most_common_class` but missing `most_common_race`, ≥5 appearances  
**Rationale**: Race field may be missing from data, but class indicates character sheet tracking  
**Lower confidence** due to incomplete data

#### Rule 7: No Class, No Race, Few Appearances → Monster (80% confidence)
**Pattern**: No class, no race, <10 appearances  
**Rationale**: Unnamed/generic monsters or environmental effects  
**Examples**: Short-lived summons, environmental hazards

#### Rule 8: Race Only (No Class), Moderate Activity → NPC (65% confidence)
**Pattern**: Has race but no class, >10 appearances  
**Rationale**: Named NPC with basic tracking but no detailed character sheet  
**Example**: Quest giver with racial identity but no combat class

#### Rule 9: Edge Cases → NPC (50% confidence)
**Pattern**: ≥3 appearances, doesn't match other rules  
**Rationale**: Conservative default for characters with some presence but unclear type  
**Low confidence** indicates high uncertainty

---

## 2. HP (Hit Points) Parsing Assumptions

### Source Format
HP stored as text: `"<current/max HP; status>"` (e.g., `"<121/121 HP; Healthy>"`)

### Parsing Rules

#### Standard Format: `<current/max HP; status>`
**Example**: `<45/60 HP; Injured>` → current=45, max=60, percentage=75.0%, status="Injured"

#### Edge Case: Current HP > Max HP
**Pattern**: `<130/121 HP; Healthy>`  
**Database Count**: 392 snapshots (0.6% of data)  
**ASSUMPTION**: Temporary HP or buff effects, **stored as-is**  
**Rationale**: 
- D&D 5e allows temporary HP above maximum
- Artificer/Abjuration Wizard features grant temp HP
- Aid spell increases max HP temporarily
- **No data modification** - preserve exact combat state

#### Edge Case: Negative HP
**Handling**: Stored as-is (indicates death saving throws state)

#### Edge Case: Missing HP Data
**Handling**: Set to NULL (not 0) - distinguishes "unknown" from "dead"

#### Health Status Extraction
**Field**: Text status after semicolon (`Healthy`, `Injured`, `Bloodied`, `Critical`)  
**Usage**: Stored separately for combat analytics

---

## 3. Class Parsing Assumptions

### Format Variations Handled

#### Single Class: `"Wizard 8"`
**Parsing**: primary_class="Wizard", level=8

#### Multiclass: `"Ranger 12/Cleric 3"`
**ASSUMPTION**: First class listed is primary (highest level)  
**Parsing**: primary_class="Ranger", level=12  
**Rationale**: Avrae convention lists highest level class first

#### Complex Multiclass: `"Fighter 5/Paladin 3/Barbarian 2"`
**Parsing**: Only extracts first class  
**Limitation**: Total level not calculated (would require summing)

#### Subclass Info: `"Blood Hunter (Order of the Lycan) 14"`
**Parsing**: Stores full text in `class_text`, extracts "Blood Hunter" as primary  
**ASSUMPTION**: Text before parentheses or level number is base class

#### Archetypes: `"Artificer (Armorer)"`  
**Stored**: Full text preserved for reference

#### Unparseable Classes
**Count**: 139 class texts failed parsing (9.3% of classes)  
**Handling**: Stored in `class_text`, `class_primary` set to NULL  
**Rationale**: Complex homebrew/multiclass better to preserve than corrupt

---

## 4. Race Parsing Assumptions

### Race Storage
**Field**: `most_common_race` in characters table  
**Method**: Counter() on all snapshots, takes most frequent value

### Race Variations
- Subraces preserved: `"Dusk (subrace)"`, `"Protector Aasimar"`, `"Air Genasi (HB)"`
- Homebrew indicator: `(HB)` suffix preserved
- Custom lineage: `"Custom Lineage"` stored as-is

### Missing Race
**Handling**: NULL (not "Unknown" string)  
**Count**: 42 characters (2.2%) have class but no race

---

## 5. Damage Extraction Assumptions

### Source Format
Damage extracted from `automation_results` text via regex patterns

### Extraction Rules

#### Pattern 1: "X deals Y damage"
**Regex**: `(\w+(?:\s+\w+)*)\s+deals?\s+(\d+)\s+damage`  
**Example**: `"Fireball deals 28 damage"` → type="Fireball", amount=28

#### Pattern 2: "X takes Y damage"
**Regex**: `(\w+(?:\s+\w+)*)\s+takes?\s+(\d+)\s+damage`  
**Example**: `"Goblin takes 15 damage"` → type="Goblin", amount=15

#### Pattern 3: "Y damage (type X)"
**Regex**: `(\d+)\s+damage\s*\(([^)]+)\)`  
**Example**: `"8 damage (fire)"` → type="fire", amount=8

### Damage Type Handling
**ASSUMPTION**: If no damage type specified, use attack/spell name as type  
**Example**: `"Longsword deals 10 damage"` → type="Longsword"

### Multiple Damage Instances
**Handling**: Each damage event stored separately  
**Example**: "Scorching Ray" with 3 rays = 3 damage_event records

### Overkill Damage
**ASSUMPTION**: All damage stored even if exceeds remaining HP  
**Rationale**: Shows attack potency for balance analysis

---

## 6. Spell/Attack/Effect Relationship Assumptions

### Memorization vs. Casting

#### Spell Memorization (Prepared Spells)
**Source**: `combat_state_before/after spells_prepared` array  
**Table**: `character_snapshot_spells` junction table  
**Count**: 528,276 memorization records  
**ASSUMPTION**: Each snapshot records current prepared spell list  
**Rationale**: Shows spell selection strategy over time

#### Spell Casting (Usage)
**Source**: `automation_results` parsing for spell execution  
**Table**: `spell_casts` table  
**Count**: 638 cast records  
**ASSUMPTION**: Only recorded if spell produces automation output  
**Limitation**: Narrative-only spells (e.g., sending, detect magic) may be undercounted

### Attack Storage

#### Attack Memorization
**Source**: `combat_state attacks_prepared` array  
**Table**: `character_snapshot_attacks` junction table  
**Count**: 308,575 attack records  
**ASSUMPTION**: All equipped weapons/attacks listed each snapshot

#### Attack Execution
**Linkage**: Damage events linked to actions by `action_id`  
**ASSUMPTION**: If damage occurs during attack action, attack was used

### Effect Duration

#### Effect Application
**Source**: `combat_state effects_active` array  
**Table**: `character_snapshot_effects` junction table  
**Count**: 66,199 effect records  
**ASSUMPTION**: Effects listed in snapshot are currently active

#### Effect Duration
**Not tracked**: Start/end times not reliably extractable  
**Limitation**: Can't determine effect trigger (cast vs. already active)

---

## 7. Character Aggregate Calculations

### Most Common Class
**Method**: `Counter()` on all `character_snapshots.class_primary` for character  
**ASSUMPTION**: Modal class is "true" class (handles temporary polymorph)  
**Edge Case**: Tie between classes → Counter returns arbitrary winner

### Most Common Race
**Method**: `Counter()` on all `character_snapshots.race`  
**ASSUMPTION**: Modal race is "true" race (handles True Polymorph effects)

### Total Appearances
**Method**: `COUNT(*)` of character_snapshots  
**Definition**: Number of combat state snapshots (before/after/target)  
**Not**: Unique combat encounters (one action may generate 20+ snapshots)  
**Rationale**: Measures data richness, not encounter count

### First/Last Seen
**Method**: MIN/MAX of `actions.timestamp` joined through snapshots  
**ASSUMPTION**: Timestamp ordering reflects chronological campaign progression  
**Limitation**: Across-campaign ordering may not be chronological

---

## 8. Referential Integrity Assumptions

### Character ID Assignment
**Method**: INSERT OR IGNORE on first character name occurrence  
**ASSUMPTION**: Character names are unique identifiers  
**Limitation**: "Bob" in Campaign A vs. Campaign B treated as same character

### Spell/Attack/Effect Deduplication
**Method**: INSERT OR IGNORE on normalized names  
**Example**: "fireball", "Fireball", "FIREBALL" → same spell_id  
**ASSUMPTION**: Case-insensitive name matching sufficient for deduplication

### Controller ID
**Field**: `character_snapshots.controller_id`  
**Source**: `combat_state controller_id`  
**ASSUMPTION**: Empty string or NULL = NPC (no player controller)  
**Usage**: Could distinguish player-controlled vs. DM-controlled

---

## 9. Data Quality Decisions

### Missing Data Handling
**Philosophy**: NULL > Placeholder strings  
**Rationale**: NULL allows SQL aggregates to work correctly (COUNT, AVG exclude NULLs)

### Data Validation Failures
**392 HP violations**: Current > Max HP → **stored as-is** (see §2)  
**139 class parse failures**: Stored full text, primary=NULL  
**No rejections**: All source records loaded despite anomalies

### Outlier Handling
**No filtering**: Extreme values (4,466 damage from DLoT1) retained  
**Rationale**: Actual game state, even if unusual (critical hits, spell combinations)

---

## 10. Tableau Export Assumptions

### Hyper Format Conversion
**Method**: Direct SQLite → Hyper column mapping  
**Schema**: `"Extract"."table_name"` namespace required by Tableau  
**Compression**: Hyper columnar format (90% size reduction: 31 MB → 3.1 MB)

### Data Type Mapping
- SQLite INTEGER → Hyper INT  
- SQLite REAL → Hyper DOUBLE  
- SQLite TEXT → Hyper TEXT  
**ASSUMPTION**: No precision loss in conversion (verified: 100% fidelity)

### Null Handling
**SQLite NULL → Hyper NULL**: Direct mapping, no sentinel values

---

## 11. Data Quality Issues Discovered

### Race Field Corruption (CRITICAL ISSUE)
**Discovered**: February 9, 2025 during PC/NPC classification review

**Problem**: Race field contains invalid data instead of D&D races/creature types

**Corruption Patterns**:
1. **Race = Character Name** (~100+ cases)
   - Examples: "Lily" with race="Lily", "Lilith" with race="Lilith", "Echo" with race="Echo"
   - Cause: Data extraction bug or field misalignment in source data
   - Impact: Pollutes race analytics, misleads classification

2. **Race = Character IDs/Hashes**
   - Examples: "wcjc3y2d8z" (alphanumeric ID)
   - Cause: Database/API IDs leaked into race field
   - Impact: Unusable for analysis

3. **Race = Full Character Names with Quotes**
   - Examples: `Uturik "Chinchillen" Rathen`
   - Cause: Name field overflow or parsing error
   - Impact: Invalid race data

4. **Race = Descriptive Text/DM Notes**
   - Examples: "Spellcaster - Healer (level 12)", "Custom Lineage Some Kind of Human but with Darkvision"
   - Cause: DM notes or homebrew descriptions in wrong field
   - Impact: Too verbose for categorical analysis

**Mitigation Strategy**:
- Heuristic validation: Detect patterns (name=race, IDs, length violations)
- LLM validation: Use LM Studio for edge cases
- Confidence threshold: ≥90% confidence → set to NULL
- Document in corruption log for future reference

**Status**: Validation script created (`validate_race_data.py`), cleaning pending

### Other Tables - Pending Validation
- ❓ Spells table: Check for ID/hash corruption in spell names
- ❓ Attacks table: Check for ID/hash corruption in attack names  
- ❓ Effects table: Check for ID/hash corruption in effect names
- ❓ Character names: Check for system tokens or IDs

---

## 12. Known Limitations & Future Considerations

### Limitations
1. **Cross-campaign conflicts**: Character names not namespaced by campaign
2. **Temporal ordering**: Unclear if timestamps are campaign-chronological or upload-chronological
3. **Narrative spells**: Under-represented if they don't trigger automation
4. **NPC ambiguity**: Low-confidence classifications need manual review
5. **Multiclass totals**: Only primary class level extracted
6. **Race data corruption**: ~5-8% of race values are corrupt/invalid (see §11)

### Assumptions Requiring Validation
- [ ] Character name uniqueness across campaigns  
- [ ] First class in multiclass string = highest level  
- [ ] Temp HP stored in current_hp field (not separate)  
- [ ] Effect snapshots = currently active (not just "known")  
- [ ] Controller ID empty string = NPC controlled
- [x] Race field reliability - **VALIDATED: Contains corruption, needs filtering**

### Recommended Future Work
1. Add campaign_id foreign key if metadata available  
2. Parse total character level from multiclass strings  
3. Manual review of 296 "Unknown" classifications (15.6%)  
4. Distinguish prepared vs. known spells (class-dependent)  
5. Extract effect durations if patterns exist

---

## Document Control

**Created**: February 9, 2025  
**Author**: Eric Medlock  
**Purpose**: Grad school data visualization project (30-hour scope)  
**Review Status**: Assumptions documented post-implementation  
**Change Log**:
- 2025-02-09: Initial documentation of all preprocessing decisions  
- 2025-02-09: Revised Rule 5 (class+race → PC default) after misclassification analysis  

---

## References

- FIREBALL Paper: Zhu et al. (2023), "FIREBALL: A Dataset of Dungeons and Dragons Actual-Play with Structured Game State Information" (ACL)  
- Avrae Bot: https://avrae.io/ (D&D Discord automation)  
- D&D 5e Rules: Temporary HP, multiclassing, death saves  
- Tableau Hyper API: Column-oriented format for analytics
