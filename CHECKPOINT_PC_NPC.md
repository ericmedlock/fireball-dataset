# CHECKPOINT: PC/NPC Classification - IN PROGRESS

## STATUS: 50% Complete

### ✓ COMPLETED
1. Added `character_type` and `classification_confidence` fields to database schema
2. Updated `load_to_sqlite.py` - schema has new columns
3. Updated `sqlite_to_hyper.py` - Hyper export includes new columns
4. Fields default to 'Unknown' and 0.0

### 🚧 IN PROGRESS: Classification Logic
Need to create script that uses LM Studio to classify characters as PC/NPC/Monster/Other

### 📋 NEXT STEPS

#### 1. Create Classification Script (`classify_characters.py`)
```python
# Use LM Studio API: http://localhost:1234/v1/chat/completions
# Model: qwen/qwen2.5-vl-7b
# For each character, send prompt with:
#   - name
#   - most_common_class
#   - most_common_race
#   - description (from first snapshot)
#   - total_appearances
# Ask: "Is this a PC, NPC, Monster, or Map/Token?"
# Return: classification + confidence (0.0-1.0)
```

#### 2. Heuristic Fallbacks (if LM Studio unavailable)
- **Definitely NPC/Other:**
  - name in ['DM', 'Map', 'dm', 'map']
  - name matches /^[A-Z]{2,4}\d+$/ (e.g., 'MA1', 'AS3', 'DLoT1')
  - no class and no race
  - total_appearances < 10
- **Likely PC:**
  - has full name (2+ words)
  - has class AND race
  - has description
  - total_appearances > 50
- **Uncertain:** Ask LLM

#### 3. Update Existing Database
```bash
python classify_characters.py  # Classify all 1,895 characters
sqlite3 fireball.db "SELECT character_type, COUNT(*) FROM characters GROUP BY character_type;"
```

#### 4. Regenerate Hyper
```bash
python sqlite_to_hyper.py  # Export with classification
```

#### 5. Test in Tableau
- Filter: `character_type = 'PC'` for player dashboards
- Filter: `character_type IN ('NPC', 'Monster')` for encounter analysis

---

## CURRENT DATABASE STATE
- **File:** fireball.db (31 MB)
- **Records:** 3,443 actions, 1,895 characters
- **character_type:** All set to 'Unknown' (needs classification)
- **Schema:** Ready for classification data

## FILES TO CREATE
- [ ] `classify_characters.py` - Main classification script using LM Studio
- [ ] `classify_characters_heuristic.py` - Fallback without LLM (optional)

## TESTING CLASSIFICATION
```bash
# Check LM Studio is running
curl http://localhost:1234/v1/models

# Test single character
python -c "
import requests
resp = requests.post('http://localhost:1234/v1/chat/completions', json={
    'model': 'qwen2.5-vl-7b',
    'messages': [{'role': 'user', 'content': 'Is \"Atramir Decimus Toran\" (Artificer, Protector Aasimar) a PC or NPC? Answer: PC or NPC'}]
})
print(resp.json())
"
```

---

## RESUME WORK HERE:
1. Start LM Studio with qwen/qwen2.5-vl-7b
2. Create `classify_characters.py` (see Next Steps #1)
3. Run classification on fireball.db
4. Verify results, regenerate Hyper
5. Continue with loading remaining 44 files
