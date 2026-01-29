# FIREBALL Dataset Loader

## Project Overview
This is a HuggingFace dataset loader for the FIREBALL dataset - a specialized D&D (Dungeons & Dragons) actual-play dataset with structured game state information from Avrae bot commands. The project implements both a HuggingFace `datasets` interface and a standalone downloader script.

**Key Paper**: Zhu et al. (2023), "FIREBALL: A Dataset of Dungeons and Dragons Actual-Play with Structured Game State Information" (ACL)

## Architecture

### Dual-Purpose Implementation
[fireball.py](fireball.py) serves two distinct roles:

1. **HuggingFace Dataset Builder** (primary): Extends `datasets.GeneratorBasedBuilder` for integration with HuggingFace's dataset ecosystem
2. **Standalone Downloader** (secondary): When run as `__main__`, downloads and exports first 10 examples to [output/fireball_data.json](output/fireball_data.json)

### Data Structure
Each FIREBALL example captures a complete D&D combat action with:
- **Temporal narrative**: `before_utterances`, `after_utterances`, `utterance_history`
- **Game state snapshots**: `combat_state_before`, `combat_state_after` (character HP, class, race, attacks, spells, effects)
- **Action data**: `commands_norm` (normalized Avrae commands), `automation_results`
- **Actor information**: `current_actor`, `caster_after`, `targets_after`
- **Index metadata**: Various `*_idxs` fields for temporal ordering

Character objects contain rich D&D metadata (see lines 74-85 for schema).

## Data Source
- **Remote dataset**: `https://huggingface.co/datasets/lara-martin/FIREBALL/raw/main/`
- Dataset split across multiple `.jsonl` files (listed in `files.txt`)
- Uses HuggingFace's `DownloadManager` for automatic caching

## Development Workflows

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # or `.venv/Scripts/activate` on Windows
pip install -r requirements.txt
```

**Dependencies**: `jsonlines`, `datasets`, `requests` (implicit for standalone mode)

### Running Modes

**Standalone download (10 examples)**:
```bash
python fireball.py
```
Output: [output/fireball_data.json](output/fireball_data.json) with first 10 records

**HuggingFace integration**:
```python
from datasets import load_dataset
dataset = load_dataset('fireball.py', name='FIREBALL')
```

### Common Issues
- Script expects `output/` directory to exist (should be pre-created)
- No validation/error handling for missing network connectivity
- Standalone mode hardcodes 10 examples (see line 260: `max_examples = 10`)

## Project-Specific Patterns

### Schema Definition
Complex nested `Features` schema (lines 70-148) mirrors D&D game state complexity:
- Use `datasets.Sequence()` for variable-length lists (utterances, indices)
- Character state represented as list of dicts (`combat_state_before/after`)
- Single actors as dict (`current_actor`, `caster_after`)

### Generator Pattern
`_generate_examples()` (lines 216-246) yields from multiple `.jsonl` files sequentially, maintaining global key counter for uniqueness across files.

## Conventions
- **Field types**: All D&D strings use `datasets.Value('string')`, IDs are `'int64'`, indices are `'int16'`
- **Null handling**: Schema allows null for optional fields (`class`, `actions`, `description`)
- **Licensing**: Apache 2.0 (code), CC-BY-4.0 (dataset) - see headers

## Future Considerations
- No test coverage exists
- Standalone mode could parameterize example count
- Missing error handling for malformed `.jsonl` data
- Could add validation for required character fields
