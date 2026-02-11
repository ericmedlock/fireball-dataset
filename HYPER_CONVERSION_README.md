# FIREBALL Dataset Conversion Tools

Complete toolkit for downloading, processing, and converting the FIREBALL D&D dataset to various formats including CSV and Tableau Hyper.

## 📋 Overview

This repository contains scripts to:
1. Download the full FIREBALL dataset (153,829 records, 2.3GB)
2. Validate JSON formatting
3. Split into manageable chunks
4. **Load into SQLite with data normalization & cleaning** ⭐ RECOMMENDED
5. **Convert to Tableau Hyper format for visualization**
6. Convert to CSV format (legacy)

## 🚀 Quick Start (Recommended: SQLite → Hyper)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Load JSON to SQLite
```bash
python load_to_sqlite.py
```
**Features:**
- ✅ Normalized star schema (dimension + fact tables)
- ✅ Automatic class filtering (14 official D&D classes only)
- ✅ Archetype extraction (separates "Champion Fighter" → Fighter + Champion)
- ✅ Character aggregate calculation
- ✅ Data quality validation
- ✅ ~31 MB per JSON file

### 3. Export to Tableau Hyper
```bash
python sqlite_to_hyper.py
```
**Output:** `fireball.hyper` (1.8 MB, 100% data fidelity, 90% compression)

### 4. Optional: Class Filtering Post-Processing
If you already have a database loaded before Feb 11, 2026:
```bash
python clean_nonstandard_classes.py
```
This will remove non-standard homebrew classes and extract archetypes.

---

## 📊 SQLite Workflow (Recommended)

### Why SQLite?
- **Clean dimensions**: Only 14 official D&D classes (no homebrew pollution)
- **Archetype extraction**: Separates subclasses into dedicated field
- **Normalized schema**: Optimized for Tableau relationships
- **Character aggregates**: Pre-calculated metrics (most_common_class, total_appearances)
- **Data quality**: Validated and cleaned during load
- **Queryable**: Test queries before Tableau

### Class Filtering
**Kept (14 classes):**
- Core PHB: Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard
- Eberron: Artificer
- Critical Role: Blood Hunter

**Removed:** Witch, Twin, SoulBinder, MagicalGirl, Magister, Warlord, etc. (13 homebrew classes)

See [CLASS_FILTERING_COMPLETE.md](CLASS_FILTERING_COMPLETE.md) for details.

### Database Schema
- **Dimension Tables**: characters, spells, attacks, effects
- **Fact Tables**: actions, character_snapshots, spell_casts, damage_events
- **Junction Tables**: character_snapshot_spells, character_snapshot_attacks, character_snapshot_effects

See [SCHEMA_GUIDE.md](SCHEMA_GUIDE.md) for complete documentation.

---

## 📚 Available Scripts

### RECOMMENDED: SQLite Workflow ⭐

#### **load_to_sqlite.py** - JSON to SQLite
Load JSON files into normalized SQLite database with automatic cleaning.

**Features:**
- ✅ Star schema with dimension/fact tables
- ✅ Automatic class filtering (14 official classes)
- ✅ Archetype extraction (class_archetype field)
- ✅ Character aggregate calculation
- ✅ Incremental loading support

**Usage:**
```bash
python load_to_sqlite.py
```
**Output:** `fireball.db` (31 MB per JSON file)

#### **sqlite_to_hyper.py** - SQLite to Hyper
Convert SQLite database to Tableau Hyper format.

**Usage:**
```bash
python sqlite_to_hyper.py
```
**Output:** `fireball.hyper` (1.8 MB, 90% compression)

#### **clean_nonstandard_classes.py** - Post-Processing
Remove non-standard classes from existing database.

**Usage:**
```bash
python clean_nonstandard_classes.py
```

---

### LEGACY: Direct JSON to Hyper (Flattened)

#### **json_to_hyper_direct.py**
Convert JSON directly to Tableau Hyper format (no normalization).

**Note:** This creates a flattened single-table structure. For better analysis, use the SQLite workflow instead.

**Features:**
- ✅ Memory-efficient streaming parser
- ✅ Flattens nested JSON structures
- ✅ 99%+ compression ratio
- ⚠️ No data normalization or cleaning

**Usage:**
```bash
python json_to_hyper_direct.py <input.json> [output.hyper] [chunk_size]
```

#### **fireball.py** - Dataset Download
Original HuggingFace dataset loader with standalone download mode.

**Usage:**
```bash
python fireball.py
```
**Output:** `output/fireball_data.json` (2.3GB, 153,829 records)

#### **validate_json.py** - Validation
Validate JSON files for proper formatting.

**Usage:**
```bash
python validate_json.py [path/to/file.json]
```

#### **split_dataset.py** - File Splitting
Split large JSON into manageable chunks.

**Usage:**
```bash
python split_dataset.py
```
**Output:** 45 files of ~50MB each in `output/split/`

---

Each record in the FIREBALL dataset contains:

| Field | Type | Description |
|-------|------|-------------|
| `speaker_id` | string | Discord user ID of the speaker |
| `before_utterances` | array | Chat messages before the action |
| `after_utterances` | array | Chat messages after the action |
| `utterance_history` | array | Full conversation history |
| `combat_state_before` | array | Character states before action |
| `combat_state_after` | array | Character states after action |
| `current_actor` | object | Active character information |
| `caster_after` | object | Spell caster state after action |
| `targets_after` | array | Affected targets |
| `commands_norm` | array | Normalized Avrae commands |
| `automation_results` | array | Command execution results |
| `before_idxs` | array | Message index references |
| `after_idxs` | array | Message index references |
| `before_state_idx` | int | State snapshot index |
| `after_state_idx` | int | State snapshot index |
| `command_idxs` | array | Command index references |
| `embed_idxs` | array | Embed message indices |

### Character Object Structure
```json
{
  "name": "Character Name",
  "hp": "<121/121 HP; Healthy>",
  "class": "Witch 17",
  "race": "Changeling",
  "attacks": "Unarmed Strike, Dagger",
  "spells": "Fireball, Magic Missile, ...",
  "actions": "Extra Attack, ...",
  "effects": "Haste, Bless, ...",
  "description": "Character description",
  "controller_id": "278369453363180276"
}
```

## 🎯 Flattening Strategy (for CSV/Hyper)

Complex nested structures are converted to JSON strings:
- **Lists** → JSON string arrays
- **Objects** → JSON string objects
- **Scalars** → Kept as-is

This preserves all data while making it compatible with tabular formats.

## 📈 Using with Tableau

### Opening Hyper Files
1. **Tableau Desktop**: File → Open → Select `.hyper` file
2. **Tableau Server**: Upload as data source
3. **Tableau Prep**: Connect to Hyper file

### Parsing Nested Data in Tableau
Use calculated fields to parse JSON strings:

```tableau
// Extract first utterance
SPLIT([before_utterances], '","', 1)

// Parse combat state (requires JSON functions in newer Tableau versions)
// Or use Tableau Prep to expand arrays before analysis
```

## 💾 File Sizes

| Format | Size | Records | Notes |
|--------|------|---------|-------|
| Original JSON | 2.23 GB | 153,829 | Full dataset |
| Split JSON (each) | ~50 MB | ~3,443 | 45 files total |
| CSV (each) | ~45 MB | ~3,443 | Slightly smaller |
| Hyper (each) | ~64 KB | ~3,443 | 99.9% compression! |

## 🔧 Troubleshooting

### Out of Memory Errors
Reduce chunk size:
```bash
python json_to_hyper_direct.py input.json output.hyper 500
```

### Hyper Process Errors
Use the direct API version (`json_to_hyper_direct.py`) instead of `json_to_hyper.py`.

### JSON Parsing Errors
Validate first:
```bash
python validate_json.py your_file.json
```

## 📝 Citation

If you use this dataset, please cite:

```bibtex
@inproceedings{Zhu2023FIREBALL,
  title={{FIREBALL: A Dataset of Dungeons and Dragons Actual-Play with Structured Game State Information}},
  author={Zhu, Andrew and Aggarwal, Karmanya and Feng, Alexander and Martin, Lara J. and Callison-Burch, Chris},
  year={2023},
  booktitle={Annual Meeting of the Association for Computational Linguistics (ACL)},
  pages={4171--4193},
  publisher={ACL}
}
```

## 📄 License

- **Code**: Apache 2.0
- **Dataset**: CC-BY-4.0

## 🔗 Resources

- [FIREBALL Paper](https://aclanthology.org/2023.acl-long.229/)
- [GitHub Repository](https://github.com/zhudotexe/FIREBALL)
- [HuggingFace Dataset](https://huggingface.co/datasets/lara-martin/FIREBALL)
