# FIREBALL Dataset Conversion Tools

Complete toolkit for downloading, processing, and converting the FIREBALL D&D dataset to various formats including CSV and Tableau Hyper.

## 📋 Overview

This repository contains scripts to:
1. Download the full FIREBALL dataset (153,829 records, 2.3GB)
2. Validate JSON formatting
3. Split into manageable chunks
4. Convert to CSV format
5. **Convert to Tableau Hyper format for visualization**

## 🚀 Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Convert JSON to Tableau Hyper
```bash
# Convert a single file
python json_to_hyper_direct.py output/fireball_data.json

# Convert a split file
python json_to_hyper_direct.py output/split/fireball_part_001_of_045.json

# Custom output name and chunk size
python json_to_hyper_direct.py input.json output.hyper 2000
```

## 📚 Available Scripts

### 1. **json_to_hyper_direct.py** ⭐ RECOMMENDED
Convert JSON to Tableau Hyper format with memory-efficient streaming.

**Features:**
- ✅ Auto-installs missing dependencies
- ✅ Memory-efficient streaming parser (handles 2.3GB+ files)
- ✅ Flattens nested JSON structures
- ✅ Direct Hyper API (most reliable)
- ✅ Progress bars and detailed logging
- ✅ 99%+ compression ratio

**Usage:**
```bash
python json_to_hyper_direct.py <input.json> [output.hyper] [chunk_size]
```

**Examples:**
```bash
# Full dataset (2.3GB)
python json_to_hyper_direct.py output/fireball_data.json fireball.hyper

# Single split file (50MB)
python json_to_hyper_direct.py output/split/fireball_part_001_of_045.json

# Custom chunk size for 16GB+ RAM
python json_to_hyper_direct.py output/fireball_data.json fireball.hyper 5000
```

**Memory Recommendations:**
- **16GB+ RAM**: `chunk_size=5000`
- **8GB RAM**: `chunk_size=1000` (default)
- **4GB RAM**: `chunk_size=500`

### 2. fireball.py
Original HuggingFace dataset loader with standalone download mode.

**Usage:**
```bash
# Download full dataset
python fireball.py
```

**Output:** `output/fireball_data.json` (2.3GB, 153,829 records)

### 3. validate_json.py
Validate JSON files for proper formatting.

**Usage:**
```bash
python validate_json.py [path/to/file.json]
```

### 4. split_dataset.py
Split large JSON into manageable chunks.

**Usage:**
```bash
python split_dataset.py
```

**Output:** 45 files of ~50MB each in `output/split/`

### 5. json_to_csv.py
Convert JSON to CSV format.

**Usage:**
```bash
# Single file
python json_to_csv.py output/split/fireball_part_001_of_045.json

# All files in directory
python json_to_csv.py --all

# Custom directory
python json_to_csv.py --dir output/split/ csv_output/
```

## 📊 Data Structure

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
