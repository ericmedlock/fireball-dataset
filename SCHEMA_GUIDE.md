# FIREBALL Dataset - Complete Schema Guide
**For Dashboard Development**  
**Updated**: February 10, 2026

---

## 🎯 TLDR - Quick Start

### What's in the Database:
- **153,829 total records** from D&D actual-play campaigns (full dataset)
- **Currently loaded**: 1 of 45 files (3,443 actions, ~2.2% of total)
- **Format**: SQLite database (`fireball.db`, 31 MB) + Tableau Hyper (`fireball.hyper`, 1.8 MB)
- **Schema type**: Star schema with dimension/fact tables + junction tables

### Core Tables for Dashboards:
1. **actions** (3,443 rows) - Combat actions/turns [FACT TABLE]
2. **characters** (1,895 rows) - Unique D&D characters [DIMENSION]
3. **character_snapshots** (61,724 rows) - Character states before/after actions [FACT TABLE]
4. **spells** (825 rows) - Spell catalog [DIMENSION]
5. **attacks** (3,179 rows) - Attack catalog [DIMENSION]
6. **damage_events** (2,760 rows) - Damage dealt per action [FACT TABLE]
7. **spell_casts** (638 rows) - Spells actually cast [FACT TABLE]

### Quick Dashboard Ideas:
- **Character Leaderboard**: Join `characters` → `damage_events` → aggregate by character
- **Spell Utilization**: Join `spells` → `character_snapshot_spells` (memorized) vs `spell_casts` (used)
- **Class Performance**: Join `characters` → `character_snapshots` → filter by `class_primary`
- **Combat Timeline**: Use `actions` with `before_state_idx` and `after_state_idx` for temporal ordering

### Key Join Paths:
```
characters.character_id = character_snapshots.character_id
characters.character_id = damage_events.attacker_id
actions.action_id = character_snapshots.action_id
actions.action_id = spell_casts.action_id
```

---

## 📊 Database Schema Overview

### Schema Type: Star Schema
- **Dimension Tables**: characters, spells, attacks, effects
- **Fact Tables**: actions, character_snapshots, spell_casts, damage_events
- **Junction Tables**: character_snapshot_spells, character_snapshot_attacks, character_snapshot_effects

### Entity-Relationship Diagram
```
┌─────────────┐
│  CHARACTERS │◄──────┐
│  (1,895)    │       │
└──────┬──────┘       │
       │              │
       │ 1:N          │ 1:N
       │              │
┌──────▼──────┐       │
│   ACTIONS   │       │
│   (3,443)   │       │
└──────┬──────┘       │
       │              │
       │ 1:N          │
       │              │
┌──────▼──────────────┴───┐
│  CHARACTER_SNAPSHOTS    │
│      (61,724)           │
└──────┬──────────────────┘
       │
       │ N:M (via junction tables)
       │
   ┌───┴───┬────────┬─────────┐
   │       │        │         │
┌──▼───┐ ┌▼─────┐ ┌▼──────┐ ┌▼──────┐
│SPELLS│ │ATTACKS│ │EFFECTS│ │DAMAGE │
│(825) │ │(3,179)│ │(699)  │ │EVENTS │
└──────┘ └───────┘ └───────┘ │(2,760)│
                              └───────┘
```

---

## 📁 Detailed Table Schemas

### 1. `characters` (Dimension Table)
**Purpose**: Unique D&D characters/monsters/NPCs across all campaigns  
**Rows**: 1,895  
**Primary Key**: `character_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `character_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `name` | TEXT | Character name (UNIQUE) | "Atramir Decimus Toran" | NO |
| `most_common_class` | TEXT | Modal class across all appearances | "Artificer" | YES (39% populated) |
| `most_common_race` | TEXT | Modal race across all appearances | "Protector Aasimar" | YES (98% populated) |
| `controller_id` | TEXT | Discord user ID of player | "278369453363180276" | YES |
| `first_seen_action_id` | INTEGER | Earliest action this character appeared | 1 | YES |
| `last_seen_action_id` | INTEGER | Latest action this character appeared | 3443 | YES |
| `total_appearances` | INTEGER | Count of snapshots | 314 | NO |
| `character_type` | TEXT | Classification: PC/NPC/Monster/Other | "PC" | NO (default: 'Unknown') |
| `classification_confidence` | REAL | Confidence score (0.0-1.0) | 0.81 | NO (default: 0.0) |

**Aggregate Calculation Rules**:
- `most_common_class`: Mode of `character_snapshots.class_primary` (most frequent value)
- `most_common_race`: Mode of `character_snapshots.race`
- `total_appearances`: COUNT(*) from `character_snapshots` for this character

**Character Types**:
- **PC (Player Character)**: 740 characters (39%), avg confidence 81%
- **Monster**: 733 characters (39%), avg confidence 94%
- **NPC**: 417 characters (18%), avg confidence 57%
- **Other**: 5 characters (<1%) - includes "DM", "Map", environment tokens

**Dashboard Uses**:
- Filter by `character_type = 'PC'` for player-focused metrics
- Join to `damage_events` for damage leaderboards
- Use `total_appearances` to filter out rare/one-off characters
- Group by `most_common_class` for class performance comparisons

---

### 2. `actions` (Fact Table)
**Purpose**: Individual combat actions/turns in D&D encounters  
**Rows**: 3,443  
**Primary Key**: `action_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `action_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `speaker_id` | TEXT | Discord user ID who issued command | "278369453363180276" | YES |
| `current_actor_id` | INTEGER | Character taking the action (FK) | 42 | YES |
| `before_state_idx` | INTEGER | Snapshot index before action | 100 | YES |
| `after_state_idx` | INTEGER | Snapshot index after action | 101 | YES |
| `command_text` | TEXT | Normalized Avrae command | "!i attack Longsword -t Goblin" | YES |
| `automation_result` | TEXT | Command execution output | "Goblin took 8 damage" | YES |
| `source_file` | TEXT | Origin JSON file | "fireball_part_001_of_045.json" | YES |

**Foreign Keys**:
- `current_actor_id` → `characters.character_id`

**Temporal Ordering**:
- Use `before_state_idx` and `after_state_idx` to reconstruct combat timeline
- State indices are relative within source file (not globally unique)

**Dashboard Uses**:
- Count of `action_id` = total combat actions
- Join to `characters` to analyze actions by character
- Parse `command_text` to categorize action types (attack, cast, help, etc.)
- Parse `automation_result` for damage/hit/miss outcomes

---

### 3. `character_snapshots` (Fact Table)
**Purpose**: Character state at specific moments (before/after actions)  
**Rows**: 61,724  
**Primary Key**: `snapshot_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `snapshot_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `action_id` | INTEGER | Associated action (FK) | 42 | NO |
| `character_id` | INTEGER | Character in this state (FK) | 15 | NO |
| `snapshot_type` | TEXT | Timing of snapshot | "before", "after", "current_actor", "caster", "target" | NO |
| `hp_current` | INTEGER | Current hit points | 121 | YES |
| `hp_max` | INTEGER | Maximum hit points | 121 | YES |
| `hp_percentage` | REAL | Current/Max * 100 | 100.0 | YES |
| `health_status` | TEXT | Parsed from HP string | "Healthy", "Bloodied", "Critical" | YES |
| `class_text` | TEXT | Raw class string | "Artificer 11" | YES |
| `class_primary` | TEXT | First/primary class | "Artificer" | YES |
| `class_level` | INTEGER | Level of primary class | 11 | YES |
| `race` | TEXT | Character race | "Harengon" | YES |
| `controller_id` | TEXT | Discord user ID | "278369453363180276" | YES |

**Foreign Keys**:
- `action_id` → `actions.action_id`
- `character_id` → `characters.character_id`

**Snapshot Types Explained**:
- `"before"`: Character status at start of combat round
- `"after"`: Character status after all actions resolved
- `"current_actor"`: The character taking the action
- `"caster"`: Character who cast a spell (post-cast state)
- `"target"`: Character affected by action (post-action state)

**HP Special Cases**:
- **Temporary HP**: `hp_current` can exceed `hp_max` (e.g., 115/110 with +5 temp HP)
- **Negative HP**: Some snapshots show negative values (dying/unconscious state)
- 392 snapshots have `current_hp > max_hp` (valid per D&D 5e rules)

**Dashboard Uses**:
- Track HP changes over time: compare `snapshot_type = 'before'` vs `'after'`
- Filter by `hp_percentage < 50` for "Bloodied" analysis
- Group by `class_primary` for class-based metrics
- Join to junction tables to see spells/attacks/effects at this moment

---

### 4. `spells` (Dimension Table)
**Purpose**: Catalog of all D&D spells referenced in dataset  
**Rows**: 825  
**Primary Key**: `spell_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `spell_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `spell_name` | TEXT | Spell name (UNIQUE) | "Fireball" | NO |

**Popularity (by memorization)**:
1. Shield - 11,631 memorizations
2. Cure Wounds - 10,706 memorizations
3. Guidance - 8,482 memorizations
4. Prestidigitation - 8,239 memorizations
5. Absorb Elements - 7,636 memorizations

**Dashboard Uses**:
- Join to `character_snapshot_spells` for "spells prepared" analysis
- Join to `spell_casts` for "spells actually cast" analysis
- Calculate utilization rate: `COUNT(spell_casts) / COUNT(snapshot_spells) * 100`

---

### 5. `attacks` (Dimension Table)
**Purpose**: Catalog of all attacks/weapons referenced in dataset  
**Rows**: 3,179  
**Primary Key**: `attack_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `attack_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `attack_name` | TEXT | Attack/weapon name (UNIQUE) | "Longsword" | NO |

**Data Quality Notes**:
- Some attack names are very long (100+ chars) due to naming conventions
- Attack names may include character names in parentheses (cleaned during load)
- Example: "Eldritch Blast (Character Name)" → "Eldritch Blast"

**Dashboard Uses**:
- Join to `character_snapshot_attacks` to see available attacks per character
- Filter by common weapons ("Longsword", "Dagger") for weapon popularity analysis
- Parse `attack_name` for weapon type categorization

---

### 6. `effects` (Dimension Table)
**Purpose**: Catalog of all active effects/conditions/buffs/debuffs  
**Rows**: 699  
**Primary Key**: `effect_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `effect_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `effect_name` | TEXT | Effect name (UNIQUE) | "Haste" | NO |

**Common Effects**:
- Buffs: Bless, Haste, Guidance, Bardic Inspiration
- Debuffs: Stunned, Poisoned, Prone, Frightened
- Damage-over-time: Burning, Bleeding
- Concentration markers: "Concentrating on Spell Name"

**Dashboard Uses**:
- Join to `character_snapshot_effects` to see active effects per character
- Count effects per snapshot to measure buff/debuff intensity
- Filter by effect category (requires text parsing)

---

### 7. `spell_casts` (Fact Table)
**Purpose**: Spells actually cast during actions (not just prepared)  
**Rows**: 638  
**Primary Key**: `cast_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `cast_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `action_id` | INTEGER | Action where spell was cast (FK) | 42 | NO |
| `character_id` | INTEGER | Caster (FK) | 15 | NO |
| `spell_id` | INTEGER | Spell cast (FK) | 101 | NO |
| `damage_dealt` | INTEGER | Total damage from this cast | 28 | YES |
| `target_count` | INTEGER | Number of targets hit | 3 | YES |

**Foreign Keys**:
- `action_id` → `actions.action_id`
- `character_id` → `characters.character_id`
- `spell_id` → `spells.spell_id`

**Extraction Logic**:
- Parsed from `actions.command_text` using pattern: `"!cast spell_name"`
- `damage_dealt` extracted from `automation_result` (e.g., "X took Y damage")
- Target count inferred from result text or `-t` flags in command

**Dashboard Uses**:
- Compare to `character_snapshot_spells` for spell utilization rates
- Group by `spell_id` to find most-cast spells
- Calculate avg damage per spell: `AVG(damage_dealt)` by spell
- Time-series: spell casts by action_id (temporal analysis)

---

### 8. `damage_events` (Fact Table)
**Purpose**: Individual damage instances dealt during actions  
**Rows**: 2,760  
**Primary Key**: `event_id`

| Column | Type | Description | Example | Nulls? |
|--------|------|-------------|---------|--------|
| `event_id` | INTEGER | Auto-increment primary key | 1, 2, 3... | NO |
| `action_id` | INTEGER | Action where damage occurred (FK) | 42 | NO |
| `attacker_id` | INTEGER | Character dealing damage (FK) | 15 | YES |
| `target_name` | TEXT | Name of damaged character | "Goblin" | NO |
| `damage_amount` | INTEGER | Hit points lost | 8 | NO |

**Foreign Keys**:
- `action_id` → `actions.action_id`
- `attacker_id` → `characters.character_id`

**Why `target_name` instead of `target_id`?**
- Some targets may not exist in `characters` table (environmental damage, etc.)
- Can be joined to `characters.name` if needed

**Top Damage Dealers**:
1. Vanessa Parker (Blood Hunter) - 48,030 total damage, 45.7 avg per hit
2. Cuco (Artificer) - 23,865 total damage, 14.7 avg per hit
3. Bella (Fighter) - 23,184 total damage, 40.3 avg per hit

**Dashboard Uses**:
- **DPS Leaderboard**: `SUM(damage_amount)` grouped by `attacker_id`
- **Damage per Action**: `AVG(damage_amount)` by character
- **Hit Count**: `COUNT(event_id)` per character (attack frequency)
- **Target Analysis**: Group by `target_name` to see who takes most damage

---

## 🔗 Junction Tables (Many-to-Many Relationships)

### 9. `character_snapshot_spells`
**Purpose**: Link snapshots to spells characters have prepared (memorized but not necessarily cast)  
**Rows**: 528,276  
**Composite Primary Key**: (`snapshot_id`, `spell_id`)

| Column | Type | Description | FK Target |
|--------|------|-------------|-----------|
| `snapshot_id` | INTEGER | Character state | `character_snapshots.snapshot_id` |
| `spell_id` | INTEGER | Prepared spell | `spells.spell_id` |

**Data Parsing**:
- Source: `combat_state_before[].spells` and `caster_after.spells` from JSON
- Spells field format: `"Fireball, Shield, Cure Wounds, ..."` (comma-separated)
- Each spell parsed and linked via junction table

**Dashboard Uses**:
- **Spell Preparation Analysis**: Most commonly prepared spells
- **Utilization Gap**: Compare to `spell_casts` to find over-prepared spells
  ```sql
  SELECT s.spell_name, 
         COUNT(DISTINCT css.snapshot_id) as prepared,
         COUNT(DISTINCT sc.cast_id) as cast,
         ROUND(COUNT(sc.cast_id) * 100.0 / COUNT(css.snapshot_id), 2) as utilization_pct
  FROM spells s
  JOIN character_snapshot_spells css ON s.spell_id = css.spell_id
  LEFT JOIN spell_casts sc ON s.spell_id = sc.spell_id
  GROUP BY s.spell_id
  ```

---

### 10. `character_snapshot_attacks`
**Purpose**: Link snapshots to attacks characters have available  
**Rows**: 308,575  
**Composite Primary Key**: (`snapshot_id`, `attack_id`)

| Column | Type | Description | FK Target |
|--------|------|-------------|-----------|
| `snapshot_id` | INTEGER | Character state | `character_snapshots.snapshot_id` |
| `attack_id` | INTEGER | Available attack | `attacks.attack_id` |

**Data Parsing**:
- Source: `combat_state_before[].attacks` from JSON
- Format: `"Longsword, Dagger, Unarmed Strike"` (comma-separated)

**Dashboard Uses**:
- Character weapon loadouts
- Most popular weapons (by availability)
- Weapons equipped vs. damage dealt correlation

---

### 11. `character_snapshot_effects`
**Purpose**: Link snapshots to active effects on characters  
**Rows**: 66,199  
**Composite Primary Key**: (`snapshot_id`, `effect_id`)

| Column | Type | Description | FK Target |
|--------|------|-------------|-----------|
| `snapshot_id` | INTEGER | Character state | `character_snapshots.snapshot_id` |
| `effect_id` | INTEGER | Active effect | `effects.effect_id` |

**Data Parsing**:
- Source: `combat_state_before[].effects` from JSON
- Format: `"Haste, Blessed, Concentration (Bless)"` (comma-separated)

**Dashboard Uses**:
- Buff/debuff prevalence
- Effect duration analysis (by tracking across snapshots)
- Correlation between effects and damage output

---

## 📋 Original JSON Schema (Raw Data)

### Structure of Each Record in Source Files
Each JSON record in `output/split/fireball_part_XXX_of_045.json` represents a single combat action:

```json
{
  "speaker_id": "278369453363180276",
  "before_utterances": ["Player says: I attack with my sword", "..."],
  "combat_state_before": [
    {
      "name": "Atramir Decimus Toran",
      "hp": "<121/121 HP; Healthy>",
      "class": "Artificer 11",
      "race": "Protector Aasimar",
      "attacks": "Longsword, Dagger, Unarmed Strike",
      "spells": "Fireball, Shield, Cure Wounds, ...",
      "actions": "Extra Attack, Second Wind",
      "effects": "Haste, Bless",
      "description": "A tall aasimar artificer with glowing eyes",
      "controller_id": "278369453363180276"
    },
    { /* ... more characters in combat ... */ }
  ],
  "current_actor": { /* Same structure as above */ },
  "commands_norm": ["!i attack Longsword -t Goblin"],
  "automation_results": ["Goblin took 8 damage"],
  "caster_after": { /* Same structure as above */ },
  "targets_after": [{ /* List of affected characters */ }],
  "combat_state_after": [{ /* Array of character states post-action */ }],
  "after_utterances": ["DM: The goblin falls!", "..."],
  "utterance_history": ["...", "...", "..."],
  "before_idxs": [99, 100],
  "before_state_idx": 100,
  "command_idxs": [101],
  "after_state_idx": 102,
  "after_idxs": [103],
  "embed_idxs": [101]
}
```

### JSON Field Mappings to Database

| JSON Field | Database Location | Transformation |
|------------|-------------------|----------------|
| `speaker_id` | `actions.speaker_id` | Direct copy |
| `before_utterances` | [NOT STORED] | Narrative text, excluded for now |
| `combat_state_before[].name` | `characters.name` + lookup | Get/create character |
| `combat_state_before[].hp` | `character_snapshots.hp_current/hp_max` | Regex parse: `<(\d+)/(\d+) HP; (.+)>` |
| `combat_state_before[].class` | `character_snapshots.class_primary/class_level` | Regex parse: `([A-Za-z ]+) (\d+)` |
| `combat_state_before[].race` | `character_snapshots.race` | Validation + cleaning |
| `combat_state_before[].attacks` | `character_snapshot_attacks` via junction | CSV split + lookup |
| `combat_state_before[].spells` | `character_snapshot_spells` via junction | CSV split + lookup |
| `combat_state_before[].effects` | `character_snapshot_effects` via junction | CSV split + lookup |
| `current_actor` | `actions.current_actor_id` + snapshot | Same transformations |
| `commands_norm` | `actions.command_text` + `spell_casts` extraction | Join with ", " + spell parsing |
| `automation_results` | `actions.automation_result` + `damage_events` | Join + damage regex |
| `caster_after` | Snapshot with `type='caster'` | Same transformations |
| `targets_after[]` | Snapshots with `type='target'` | Same transformations |
| `combat_state_after[]` | Snapshots with `type='after'` | Same transformations |
| `before_state_idx` | `actions.before_state_idx` | Direct copy |
| `after_state_idx` | `actions.after_state_idx` | Direct copy |

---

## 🔍 Data Quality Notes

### 1. Race Field Corruption (⚠️ 100-150 characters affected)
**Problem**: Race field contains invalid data in some records

**Examples of Corruption**:
- Race = Character name itself (e.g., `race="Lily"` for character "Lily")
- Race = Character IDs (e.g., `race="wcjc3y2d8z"`)
- Race = Full names with quotes (e.g., `race='Uturik "Chinchillen" Rathen'`)
- Race = Descriptive text (e.g., `race="Spellcaster - Healer (level 12)"`)

**How It's Handled**:
- **Heuristic validation** during load: Checks length, special chars, name matches
- **Corrupted values set to NULL** in database
- **Affects `characters.most_common_race`**: May be NULL for affected characters
- **Valid monster types preserved**: "Skeleton", "Zombie", etc. allowed even if they match name

**For Dashboards**: Filter out NULL race values or expect some characters without race data

---

### 2. Attack Name Cleaning
**Problem**: Some attack names are excessively long (100+ characters)

**Examples**:
- `"Eldritch Blast (Character Name) - Additional Descriptive Text"`
- `"Longsword +1 (Magical, Gifted by King Rothgar in Session 42)"`

**How It's Handled**:
- Parentheses at end removed: `(Character Name)` stripped
- Text after dash/colon trimmed if result still too long
- Truncated to 40 chars if necessary
- **Cleaning logged** in `data_cleaning_log.json`

**For Dashboards**: Attack names are cleaned but may lose some descriptive detail

---

### 3. HP Edge Cases
**Special Cases**:
- **Temporary HP**: 392 snapshots have `hp_current > hp_max` (VALID per D&D rules)
- **Negative HP**: Some characters have negative current HP (dying/unconscious)
- **Zero max HP**: Rare edge cases where max HP is 0 (tokens/objects)

**For Dashboards**: Use `hp_percentage` carefully, may exceed 100% or be negative

---

### 4. Multiclass Parsing
**Challenge**: Characters with multiple classes

**Examples**:
- `"Wizard 8/Artificer 3/Blood Hunter 2"` → Takes first: `"Wizard"`, level `8`
- `"Ranger 12/Cleric 3"` → `"Ranger"`, level `12`

**Limitation**: Only primary (first) class captured in `class_primary`/`class_level`  
**Workaround**: Full multiclass string preserved in `class_text` for custom parsing

---

### 5. Missing Data Prevalence
- **Characters with class**: 746 (39%) - Many NPCs/monsters don't have classes
- **Characters with race**: 1,853 (98%)
- **Characters with controller_id**: ~60% (NPCs/monsters have NULL)

**For Dashboards**: Always use LEFT JOINs and handle NULLs appropriately

---

## 🎨 Tableau Hyper File Format

### Hyper File Structure
**File**: `fireball.hyper` (1.8 MB)  
**Table**: `Extract` (single flat table)

### Flattening Strategy
- **Scalar fields**: Kept as-is (integers, strings)
- **Arrays**: Converted to JSON strings
  - Example: `before_utterances` → `'["Text 1", "Text 2"]'`
- **Objects**: Converted to JSON strings
  - Example: `current_actor` → `'{"name": "Atramir", "hp": "...", ...}'`
- **Lists of objects**: Converted to JSON strings
  - Example: `combat_state_before` → `'[{"name": "...", ...}, {...}]'`

### Column Types in Hyper
All columns are `TEXT` type to preserve nested structures

### Parsing JSON in Tableau
**Example calculated fields**:

```tableau
// Extract first utterance
SPLIT([before_utterances], '","', 1)

// Count characters in combat
// Note: Requires JSON parsing (Tableau 2020.4+)
// Alternative: Use Tableau Prep to pre-expand arrays

// Extract current actor name
// Parse [current_actor] JSON string for "name" field
```

**Recommendation**: For complex dashboards, use the SQLite database directly or load into Tableau Server with proper data model

---

## 💡 Common Dashboard Patterns

### Pattern 1: Character DPS Leaderboard
```sql
SELECT 
  c.name,
  c.most_common_class,
  c.most_common_race,
  SUM(de.damage_amount) as total_damage,
  COUNT(de.event_id) as hit_count,
  ROUND(AVG(de.damage_amount), 1) as avg_damage_per_hit,
  COUNT(DISTINCT a.action_id) as action_count
FROM characters c
LEFT JOIN damage_events de ON c.character_id = de.attacker_id
LEFT JOIN actions a ON de.action_id = a.action_id
WHERE c.character_type = 'PC'
GROUP BY c.character_id
ORDER BY total_damage DESC
LIMIT 20;
```

**Tableau Equivalent**:
- Data Source: `characters` (LEFT JOIN `damage_events` on `character_id = attacker_id`)
- Rows: `name`
- Columns: `SUM(damage_amount)`, `AVG(damage_amount)`, `COUNT(event_id)`
- Filter: `character_type = 'PC'`
- Sort: Descending by total damage

---

### Pattern 2: Spell Utilization Funnel
```sql
SELECT 
  s.spell_name,
  COUNT(DISTINCT css.snapshot_id) as times_prepared,
  COUNT(DISTINCT sc.cast_id) as times_cast,
  ROUND(COUNT(sc.cast_id) * 100.0 / NULLIF(COUNT(css.snapshot_id), 0), 2) as utilization_pct
FROM spells s
JOIN character_snapshot_spells css ON s.spell_id = css.spell_id
LEFT JOIN spell_casts sc ON s.spell_id = sc.spell_id
GROUP BY s.spell_id
HAVING times_prepared > 50  -- Filter for commonly prepared spells
ORDER BY times_prepared DESC;
```

**Tableau Equivalent**:
- Data Source: `spells` (JOIN `character_snapshot_spells`, LEFT JOIN `spell_casts`)
- Rows: `spell_name`
- Columns: `COUNTD(snapshot_id)`, `COUNTD(cast_id)`
- Calculated Field: `utilization_pct = COUNTD([cast_id]) / COUNTD([snapshot_id]) * 100`
- Visualization: Waterfall chart or bar chart

---

### Pattern 3: Class Performance Comparison
```sql
SELECT 
  c.most_common_class,
  COUNT(DISTINCT c.character_id) as character_count,
  AVG(c.total_appearances) as avg_appearances,
  SUM(de.damage_amount) as total_damage,
  COUNT(de.event_id) as total_hits,
  ROUND(AVG(de.damage_amount), 1) as avg_damage_per_hit
FROM characters c
LEFT JOIN damage_events de ON c.character_id = de.attacker_id
WHERE c.most_common_class IS NOT NULL
  AND c.character_type = 'PC'
GROUP BY c.most_common_class
HAVING character_count >= 5  -- Filter for classes with 5+ characters
ORDER BY total_damage DESC;
```

**Tableau Equivalent**:
- Data Source: `characters` (LEFT JOIN `damage_events`)
- Rows: `most_common_class`
- Columns: `SUM(damage_amount)`, `AVG(damage_amount)`, `COUNTD(character_id)`
- Filter: `most_common_class IS NOT NULL AND character_type = 'PC'`
- Visualization: Grouped bar chart or bullet chart

---

### Pattern 4: Combat Timeline (HP Changes)
```sql
SELECT 
  a.action_id,
  c.name,
  cs.snapshot_type,
  cs.hp_current,
  cs.hp_max,
  cs.hp_percentage
FROM character_snapshots cs
JOIN actions a ON cs.action_id = a.action_id
JOIN characters c ON cs.character_id = c.character_id
WHERE c.name = 'Atramir Decimus Toran'  -- Single character
ORDER BY a.action_id, cs.snapshot_type;
```

**Tableau Equivalent**:
- Data Source: `character_snapshots` (JOIN `actions`, `characters`)
- Rows: `action_id` (continuous)
- Columns: `hp_percentage`
- Filter: `name = 'Atramir Decimus Toran'`
- Mark: Line chart with dual axis (before/after snapshots)
- Color: `snapshot_type`

---

### Pattern 5: Effect Prevalence
```sql
SELECT 
  e.effect_name,
  COUNT(DISTINCT cse.snapshot_id) as times_active,
  COUNT(DISTINCT cs.character_id) as unique_characters_affected,
  ROUND(AVG(cs.hp_percentage), 1) as avg_hp_when_active
FROM effects e
JOIN character_snapshot_effects cse ON e.effect_id = cse.effect_id
JOIN character_snapshots cs ON cse.snapshot_id = cs.snapshot_id
GROUP BY e.effect_id
ORDER BY times_active DESC
LIMIT 20;
```

**Tableau Equivalent**:
- Data Source: `effects` (JOIN `character_snapshot_effects`, `character_snapshots`)
- Rows: `effect_name`
- Columns: `COUNTD(snapshot_id)`, `COUNTD(character_id)`, `AVG(hp_percentage)`
- Sort: Descending by count
- Visualization: Horizontal bar chart

---

## 🚀 Loading Full Dataset

### Current Status
- **Loaded**: 1 of 45 files (2.2% of full dataset)
- **Database size**: 31 MB
- **Hyper size**: 1.8 MB

### To Load Remaining Files
```bash
# Option 1: Modify load_to_sqlite.py to append (recommended)
python load_to_sqlite.py  # Will load all 45 files sequentially

# Option 2: Load one file at a time
python load_to_sqlite.py output/split/fireball_part_002_of_045.json
python load_to_sqlite.py output/split/fireball_part_003_of_045.json
# ... etc
```

### Expected Final Sizes
- **Database**: ~1.4 GB (31 MB × 45)
- **Hyper file**: ~140 MB (3.1 MB × 45)
- **Total actions**: ~155,000
- **Total snapshots**: ~2.7 million
- **Total characters**: ~10,000-15,000 (estimated)

### Estimated Load Time
- **Per file**: ~20-30 seconds
- **All 45 files**: ~30-45 minutes

---

## 📖 Additional Resources

### Documentation Files
- [`ASSUMPTIONS.md`](ASSUMPTIONS.md) - All data preprocessing decisions and rules
- [`DATABASE_SUMMARY.md`](DATABASE_SUMMARY.md) - Initial SQLite creation summary
- [`CHARACTER_AGGREGATES_COMPLETE.md`](CHARACTER_AGGREGATES_COMPLETE.md) - Character aggregate field documentation
- [`CHECKPOINT_DATA_QUALITY.md`](CHECKPOINT_DATA_QUALITY.md) - Data quality issues and classification
- [`HYPER_CONVERSION_README.md`](HYPER_CONVERSION_README.md) - Guide to Hyper file conversion

### Scripts
- `load_to_sqlite.py` - SQLite database loader (891 lines)
- `json_to_hyper_direct.py` - Hyper file converter (303 lines)
- `sqlite_to_hyper.py` - SQLite to Hyper converter
- `classify_characters.py` - PC/NPC/Monster classification (329 lines)
- `validate_race_data.py` - Race field validation (248 lines)

### Source Data
- Location: `output/split/`
- Files: `fireball_part_001_of_045.json` through `fireball_part_045_of_045.json`
- Size per file: ~50 MB
- Records per file: ~3,400

---

## ❓ Quick Reference

### Most Important Tables for Dashboards
1. **characters** - Character master list
2. **damage_events** - Who dealt damage to whom
3. **character_snapshots** - Character states (HP, class, race, etc.)
4. **spell_casts** - Spells actually used
5. **character_snapshot_spells** - Spells prepared (not used)

### Key Join Relationships
```
characters ← damage_events (via attacker_id)
characters ← character_snapshots (via character_id)
actions ← character_snapshots (via action_id)
actions ← spell_casts (via action_id)
actions ← damage_events (via action_id)
spells ← spell_casts (via spell_id)
spells ← character_snapshot_spells (via spell_id)
```

### Essential Filters
- `character_type = 'PC'` - Focus on player characters only
- `most_common_class IS NOT NULL` - Exclude characters without classes
- `total_appearances > 10` - Filter out rare/one-off characters
- `hp_percentage <= 100` - Exclude temporary HP edge cases

### Common Calculations
```sql
-- DPS (Damage Per Second, actually per action)
SUM(damage_amount) / COUNT(DISTINCT action_id)

-- Spell Utilization Rate
COUNT(spell_casts) * 100.0 / COUNT(snapshot_spells)

-- Hit Rate (assuming you track misses separately)
COUNT(damage_events) / COUNT(attack_attempts)

-- Average HP Loss Per Action
AVG(hp_before - hp_after)
```

---

**Need help?** Check the documentation files listed above or examine the loader scripts for specific transformation logic.
