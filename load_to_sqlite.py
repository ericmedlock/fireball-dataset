#!/usr/bin/env python3
"""
Load FIREBALL JSON data into SQLite database with normalized schema.
Implements the proposed schema and loads a single JSON file for testing.
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

class FireballDBLoader:
    def __init__(self, db_path: str = "fireball.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Create database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✓ Connected to database: {self.db_path}")
        
    def create_schema(self):
        """Create normalized database schema."""
        print("\nCreating database schema...")
        
        # Dimension: Characters
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                character_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                most_common_class TEXT,
                most_common_race TEXT,
                controller_id TEXT,
                first_seen_action_id INTEGER,
                last_seen_action_id INTEGER,
                total_appearances INTEGER DEFAULT 0,
                character_type TEXT DEFAULT 'Unknown',
                classification_confidence REAL DEFAULT 0.0
            )
        """)
        
        # Dimension: Spells
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS spells (
                spell_id INTEGER PRIMARY KEY AUTOINCREMENT,
                spell_name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Dimension: Attacks
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attacks (
                attack_id INTEGER PRIMARY KEY AUTOINCREMENT,
                attack_name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Dimension: Effects
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS effects (
                effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
                effect_name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Fact: Actions
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                speaker_id TEXT,
                current_actor_id INTEGER,
                before_state_idx INTEGER,
                after_state_idx INTEGER,
                command_text TEXT,
                automation_result TEXT,
                source_file TEXT,
                FOREIGN KEY (current_actor_id) REFERENCES characters(character_id)
            )
        """)
        
        # Fact: Character Snapshots
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                snapshot_type TEXT NOT NULL, -- 'before', 'after', 'current_actor', 'caster', 'target'
                hp_current INTEGER,
                hp_max INTEGER,
                hp_percentage REAL,
                health_status TEXT,
                class_text TEXT,
                class_primary TEXT,
                class_level INTEGER,
                race TEXT,
                controller_id TEXT,
                FOREIGN KEY (action_id) REFERENCES actions(action_id),
                FOREIGN KEY (character_id) REFERENCES characters(character_id)
            )
        """)
        
        # Junction: Character Snapshot Spells
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_snapshot_spells (
                snapshot_id INTEGER NOT NULL,
                spell_id INTEGER NOT NULL,
                PRIMARY KEY (snapshot_id, spell_id),
                FOREIGN KEY (snapshot_id) REFERENCES character_snapshots(snapshot_id),
                FOREIGN KEY (spell_id) REFERENCES spells(spell_id)
            )
        """)
        
        # Junction: Character Snapshot Attacks
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_snapshot_attacks (
                snapshot_id INTEGER NOT NULL,
                attack_id INTEGER NOT NULL,
                PRIMARY KEY (snapshot_id, attack_id),
                FOREIGN KEY (snapshot_id) REFERENCES character_snapshots(snapshot_id),
                FOREIGN KEY (attack_id) REFERENCES attacks(attack_id)
            )
        """)
        
        # Junction: Character Snapshot Effects
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_snapshot_effects (
                snapshot_id INTEGER NOT NULL,
                effect_id INTEGER NOT NULL,
                PRIMARY KEY (snapshot_id, effect_id),
                FOREIGN KEY (snapshot_id) REFERENCES character_snapshots(snapshot_id),
                FOREIGN KEY (effect_id) REFERENCES effects(effect_id)
            )
        """)
        
        # Fact: Spell Casts
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS spell_casts (
                cast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                spell_id INTEGER NOT NULL,
                damage_dealt INTEGER,
                target_count INTEGER,
                FOREIGN KEY (action_id) REFERENCES actions(action_id),
                FOREIGN KEY (character_id) REFERENCES characters(character_id),
                FOREIGN KEY (spell_id) REFERENCES spells(spell_id)
            )
        """)
        
        # Fact: Damage Events
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS damage_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                attacker_id INTEGER,
                target_name TEXT NOT NULL,
                damage_amount INTEGER NOT NULL,
                FOREIGN KEY (action_id) REFERENCES actions(action_id),
                FOREIGN KEY (attacker_id) REFERENCES characters(character_id)
            )
        """)
        
        self.conn.commit()
        print("✓ Schema created successfully")
        
    def parse_hp(self, hp_text: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[float], Optional[str]]:
        """Parse HP string like '<121/121 HP; Healthy>' into components."""
        if not hp_text or hp_text == "":
            return None, None, None, None
            
        match = re.match(r'<(\d+)/(\d+) HP; (.+?)>', hp_text)
        if match:
            current = int(match.group(1))
            max_hp = int(match.group(2))
            status = match.group(3)
            percentage = (current / max_hp * 100) if max_hp > 0 else 0
            return current, max_hp, percentage, status
        return None, None, None, None
        
    def parse_class(self, class_text: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
        """Parse class string like 'Witch 17' or 'Ranger 12/Cleric 3' into primary class and level."""
        if not class_text or class_text == "":
            return None, None
            
        # Handle multiclass by taking first class
        parts = class_text.split('/')
        if parts:
            match = re.match(r'([A-Za-z\s]+)\s+(\d+)', parts[0].strip())
            if match:
                return match.group(1).strip(), int(match.group(2))
        return class_text, None
        
    def get_or_create_character(self, name: str, controller_id: str = None) -> int:
        """Get character_id or create new character."""
        self.cursor.execute("SELECT character_id FROM characters WHERE name = ?", (name,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
            
        # Create new character
        self.cursor.execute("""
            INSERT INTO characters (name, controller_id, total_appearances)
            VALUES (?, ?, 0)
        """, (name, controller_id))
        return self.cursor.lastrowid
        
    def get_or_create_spell(self, spell_name: str) -> int:
        """Get spell_id or create new spell."""
        spell_name = spell_name.strip()
        if not spell_name:
            return None
            
        self.cursor.execute("SELECT spell_id FROM spells WHERE spell_name = ?", (spell_name,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
            
        self.cursor.execute("INSERT INTO spells (spell_name) VALUES (?)", (spell_name,))
        return self.cursor.lastrowid
        
    def get_or_create_attack(self, attack_name: str) -> int:
        """Get attack_id or create new attack."""
        attack_name = attack_name.strip()
        if not attack_name:
            return None
            
        self.cursor.execute("SELECT attack_id FROM attacks WHERE attack_name = ?", (attack_name,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
            
        self.cursor.execute("INSERT INTO attacks (attack_name) VALUES (?)", (attack_name,))
        return self.cursor.lastrowid
        
    def get_or_create_effect(self, effect_name: str) -> int:
        """Get effect_id or create new effect."""
        effect_name = effect_name.strip()
        if not effect_name:
            return None
            
        self.cursor.execute("SELECT effect_id FROM effects WHERE effect_name = ?", (effect_name,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
            
        self.cursor.execute("INSERT INTO effects (effect_name) VALUES (?)", (effect_name,))
        return self.cursor.lastrowid
        
    def parse_damage_from_automation(self, automation_text: str) -> List[Tuple[str, int]]:
        """Extract damage events from automation results."""
        damages = []
        if not automation_text:
            return damages
            
        # Pattern: "X took Y damage"
        matches = re.findall(r'(\w+)\s+took\s+(\d+)\s+damage', automation_text, re.IGNORECASE)
        for target, amount in matches:
            damages.append((target, int(amount)))
        return damages
        
    def parse_spell_from_command(self, command: str) -> Optional[str]:
        """Extract spell name from command like '!cast fireball -t enemy'."""
        if not command:
            return None
            
        # Pattern: !cast SPELLNAME or !c SPELLNAME
        match = re.match(r'!c(?:ast)?\s+([a-zA-Z\s]+)', command, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
        
    def load_character_snapshot(self, action_id: int, character_data: Dict, snapshot_type: str, source_file: str) -> Optional[int]:
        """Load a character snapshot and return snapshot_id."""
        if not character_data or not character_data.get('name'):
            return None
            
        # Get or create character
        character_id = self.get_or_create_character(
            character_data['name'],
            character_data.get('controller_id')
        )
        
        # Parse HP
        hp_current, hp_max, hp_pct, health_status = self.parse_hp(character_data.get('hp'))
        
        # Parse class
        class_primary, class_level = self.parse_class(character_data.get('class'))
        
        # Insert snapshot
        self.cursor.execute("""
            INSERT INTO character_snapshots (
                action_id, character_id, snapshot_type,
                hp_current, hp_max, hp_percentage, health_status,
                class_text, class_primary, class_level, race, controller_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action_id, character_id, snapshot_type,
            hp_current, hp_max, hp_pct, health_status,
            character_data.get('class'), class_primary, class_level,
            character_data.get('race'), character_data.get('controller_id')
        ))
        snapshot_id = self.cursor.lastrowid
        
        # Parse and link spells
        spells_text = character_data.get('spells', '')
        if spells_text and spells_text.strip():
            for spell_name in spells_text.split(','):
                spell_name = spell_name.strip()
                if spell_name:
                    spell_id = self.get_or_create_spell(spell_name)
                    self.cursor.execute("""
                        INSERT OR IGNORE INTO character_snapshot_spells (snapshot_id, spell_id)
                        VALUES (?, ?)
                    """, (snapshot_id, spell_id))
        
        # Parse and link attacks
        attacks_text = character_data.get('attacks', '')
        if attacks_text and attacks_text.strip():
            for attack_name in attacks_text.split(','):
                attack_name = attack_name.strip()
                if attack_name:
                    attack_id = self.get_or_create_attack(attack_name)
                    self.cursor.execute("""
                        INSERT OR IGNORE INTO character_snapshot_attacks (snapshot_id, attack_id)
                        VALUES (?, ?)
                    """, (snapshot_id, attack_id))
        
        # Parse and link effects
        effects_text = character_data.get('effects', '')
        if effects_text and effects_text.strip():
            for effect_name in effects_text.split(','):
                effect_name = effect_name.strip()
                if effect_name:
                    effect_id = self.get_or_create_effect(effect_name)
                    self.cursor.execute("""
                        INSERT OR IGNORE INTO character_snapshot_effects (snapshot_id, effect_id)
                        VALUES (?, ?)
                    """, (snapshot_id, effect_id))
        
        return snapshot_id
        
    def load_action(self, action_data: Dict, source_file: str) -> int:
        """Load a single action and all related data."""
        # Get current actor character_id
        current_actor_id = None
        if action_data.get('current_actor') and action_data['current_actor'].get('name'):
            current_actor_id = self.get_or_create_character(
                action_data['current_actor']['name'],
                action_data['current_actor'].get('controller_id')
            )
        
        # Combine commands and automation results
        command_text = ' | '.join(action_data.get('commands_norm', []))
        automation_text = ' | '.join(action_data.get('automation_results', []))
        
        # Insert action
        self.cursor.execute("""
            INSERT INTO actions (
                speaker_id, current_actor_id, before_state_idx, after_state_idx,
                command_text, automation_result, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            action_data.get('speaker_id'),
            current_actor_id,
            action_data.get('before_state_idx'),
            action_data.get('after_state_idx'),
            command_text,
            automation_text,
            source_file
        ))
        action_id = self.cursor.lastrowid
        
        # Load combat_state_before snapshots
        for char_data in action_data.get('combat_state_before', []):
            self.load_character_snapshot(action_id, char_data, 'before', source_file)
        
        # Load combat_state_after snapshots
        for char_data in action_data.get('combat_state_after', []):
            self.load_character_snapshot(action_id, char_data, 'after', source_file)
        
        # Load current_actor snapshot
        if action_data.get('current_actor'):
            self.load_character_snapshot(action_id, action_data['current_actor'], 'current_actor', source_file)
        
        # Load caster_after snapshot
        if action_data.get('caster_after'):
            self.load_character_snapshot(action_id, action_data['caster_after'], 'caster', source_file)
        
        # Load targets_after snapshots
        for char_data in action_data.get('targets_after', []):
            self.load_character_snapshot(action_id, char_data, 'target', source_file)
        
        # Parse spell casts
        for command in action_data.get('commands_norm', []):
            spell_name = self.parse_spell_from_command(command)
            if spell_name and current_actor_id:
                spell_id = self.get_or_create_spell(spell_name)
                
                # Parse damage from automation
                total_damage = 0
                target_count = 0
                if automation_text:
                    damages = self.parse_damage_from_automation(automation_text)
                    total_damage = sum(d[1] for d in damages)
                    target_count = len(set(d[0] for d in damages))
                
                self.cursor.execute("""
                    INSERT INTO spell_casts (action_id, character_id, spell_id, damage_dealt, target_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (action_id, current_actor_id, spell_id, total_damage if total_damage > 0 else None, target_count))
        
        # Parse damage events
        if automation_text and current_actor_id:
            damages = self.parse_damage_from_automation(automation_text)
            for target_name, amount in damages:
                self.cursor.execute("""
                    INSERT INTO damage_events (action_id, attacker_id, target_name, damage_amount)
                    VALUES (?, ?, ?, ?)
                """, (action_id, current_actor_id, target_name, amount))
        
        return action_id
        
    def load_json_file(self, json_path: str):
        """Load a single JSON file into the database."""
        print(f"\nLoading JSON file: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"  Records to process: {len(data)}")
        
        source_file = Path(json_path).name
        processed = 0
        
        for action_data in data:
            self.load_action(action_data, source_file)
            processed += 1
            
            if processed % 100 == 0:
                print(f"  Processed {processed}/{len(data)} actions...")
                self.conn.commit()  # Commit periodically
        
        self.conn.commit()
        print(f"✓ Loaded {processed} actions from {source_file}")
        
    def verify_data_integrity(self):
        """Run integrity checks on loaded data."""
        print("\n" + "="*60)
        print("DATA INTEGRITY VERIFICATION")
        print("="*60)
        
        checks_passed = 0
        checks_failed = 0
        
        # Check 1: Row counts
        print("\n1. Row Counts:")
        tables = ['characters', 'spells', 'attacks', 'effects', 'actions', 
                  'character_snapshots', 'spell_casts', 'damage_events',
                  'character_snapshot_spells', 'character_snapshot_attacks', 'character_snapshot_effects']
        
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            print(f"   {table:30s}: {count:,} rows")
        
        # Check 2: Referential integrity
        print("\n2. Referential Integrity:")
        
        # Check all character_ids in actions exist
        self.cursor.execute("""
            SELECT COUNT(*) FROM actions a
            LEFT JOIN characters c ON a.current_actor_id = c.character_id
            WHERE a.current_actor_id IS NOT NULL AND c.character_id IS NULL
        """)
        orphaned = self.cursor.fetchone()[0]
        if orphaned == 0:
            print(f"   ✓ All actions.current_actor_id reference valid characters")
            checks_passed += 1
        else:
            print(f"   ✗ {orphaned} actions have invalid current_actor_id")
            checks_failed += 1
        
        # Check all snapshots reference valid actions
        self.cursor.execute("""
            SELECT COUNT(*) FROM character_snapshots cs
            LEFT JOIN actions a ON cs.action_id = a.action_id
            WHERE a.action_id IS NULL
        """)
        orphaned = self.cursor.fetchone()[0]
        if orphaned == 0:
            print(f"   ✓ All snapshots reference valid actions")
            checks_passed += 1
        else:
            print(f"   ✗ {orphaned} snapshots have invalid action_id")
            checks_failed += 1
        
        # Check all snapshots reference valid characters
        self.cursor.execute("""
            SELECT COUNT(*) FROM character_snapshots cs
            LEFT JOIN characters c ON cs.character_id = c.character_id
            WHERE c.character_id IS NULL
        """)
        orphaned = self.cursor.fetchone()[0]
        if orphaned == 0:
            print(f"   ✓ All snapshots reference valid characters")
            checks_passed += 1
        else:
            print(f"   ✗ {orphaned} snapshots have invalid character_id")
            checks_failed += 1
        
        # Check 3: Data quality
        print("\n3. Data Quality:")
        
        # Check HP parsing
        self.cursor.execute("""
            SELECT COUNT(*) FROM character_snapshots 
            WHERE hp_current IS NOT NULL AND hp_max IS NOT NULL AND hp_current > hp_max
        """)
        invalid_hp = self.cursor.fetchone()[0]
        if invalid_hp == 0:
            print(f"   ✓ All HP values are valid (current <= max)")
            checks_passed += 1
        else:
            print(f"   ✗ {invalid_hp} snapshots have current HP > max HP")
            checks_failed += 1
        
        # Check class parsing
        self.cursor.execute("""
            SELECT COUNT(*) FROM character_snapshots 
            WHERE class_text IS NOT NULL AND class_text != '' 
            AND (class_primary IS NULL OR class_level IS NULL)
        """)
        unparsed_class = self.cursor.fetchone()[0]
        if unparsed_class == 0:
            print(f"   ✓ All class fields parsed successfully")
            checks_passed += 1
        else:
            print(f"   ⚠ {unparsed_class} class texts couldn't be fully parsed (may be ok for complex multiclass)")
        
        # Check 4: Sample data verification
        print("\n4. Sample Data Verification:")
        
        # Show top 5 characters by appearances
        self.cursor.execute("""
            SELECT c.name, c.most_common_class, COUNT(cs.snapshot_id) as snapshots
            FROM characters c
            LEFT JOIN character_snapshots cs ON c.character_id = cs.character_id
            GROUP BY c.character_id
            ORDER BY snapshots DESC
            LIMIT 5
        """)
        print("   Top 5 characters by snapshot count:")
        for name, cls, count in self.cursor.fetchall():
            print(f"     - {name:30s} ({cls or 'unknown':20s}): {count:,} snapshots")
        
        # Show top 5 spells by memorization
        self.cursor.execute("""
            SELECT s.spell_name, COUNT(css.snapshot_id) as memorizations
            FROM spells s
            JOIN character_snapshot_spells css ON s.spell_id = css.spell_id
            GROUP BY s.spell_id
            ORDER BY memorizations DESC
            LIMIT 5
        """)
        print("\n   Top 5 spells by memorization:")
        for spell, count in self.cursor.fetchall():
            print(f"     - {spell:30s}: {count:,} times")
        
        # Show top 5 spells by casting
        self.cursor.execute("""
            SELECT s.spell_name, COUNT(sc.cast_id) as casts, 
                   AVG(sc.damage_dealt) as avg_damage
            FROM spells s
            JOIN spell_casts sc ON s.spell_id = sc.spell_id
            GROUP BY s.spell_id
            ORDER BY casts DESC
            LIMIT 5
        """)
        print("\n   Top 5 spells by casting:")
        for spell, casts, avg_dmg in self.cursor.fetchall():
            dmg_str = f"{avg_dmg:.1f}" if avg_dmg else "N/A"
            print(f"     - {spell:30s}: {casts:,} casts (avg damage: {dmg_str})")
        
        # Summary
        print("\n" + "="*60)
        print(f"VERIFICATION SUMMARY: {checks_passed} passed, {checks_failed} failed")
        print("="*60)
        
        if checks_failed == 0:
            print("✓ All integrity checks passed!")
            return True
        else:
            print(f"⚠ {checks_failed} checks failed - review issues above")
            return False
        
    def populate_character_aggregates(self):
        """Calculate and populate character summary statistics."""
        print("\n" + "="*60)
        print("POST-PROCESSING: Character Aggregates")
        print("="*60)
        
        from collections import Counter
        
        # Get all characters
        self.cursor.execute("SELECT character_id, name FROM characters")
        characters = self.cursor.fetchall()
        print(f"\nCalculating aggregates for {len(characters):,} characters...")
        
        updated = 0
        
        for char_id, char_name in characters:
            # Get all snapshots for this character
            self.cursor.execute("""
                SELECT class_primary, race, action_id
                FROM character_snapshots
                WHERE character_id = ?
            """, (char_id,))
            snapshots = self.cursor.fetchall()
            
            if not snapshots:
                continue
            
            # Extract data
            classes = [s[0] for s in snapshots if s[0]]
            races = [s[1] for s in snapshots if s[1]]
            action_ids = [s[2] for s in snapshots if s[2]]
            
            # Calculate aggregates
            most_common_class = Counter(classes).most_common(1)[0][0] if classes else None
            most_common_race = Counter(races).most_common(1)[0][0] if races else None
            first_action = min(action_ids) if action_ids else None
            last_action = max(action_ids) if action_ids else None
            total_appearances = len(snapshots)
            
            # Update character record
            self.cursor.execute("""
                UPDATE characters
                SET most_common_class = ?,
                    most_common_race = ?,
                    first_seen_action_id = ?,
                    last_seen_action_id = ?,
                    total_appearances = ?
                WHERE character_id = ?
            """, (most_common_class, most_common_race, first_action, last_action, 
                  total_appearances, char_id))
            
            updated += 1
            
            if updated % 500 == 0:
                print(f"  Processed {updated}/{len(characters)} characters...")
                self.conn.commit()
        
        self.conn.commit()
        print(f"✓ Updated {updated:,} character records with aggregates")
        
        # Quick verification
        self.cursor.execute("SELECT COUNT(*) FROM characters WHERE most_common_class IS NOT NULL")
        class_count = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM characters WHERE total_appearances > 0")
        appearance_count = self.cursor.fetchone()[0]
        
        print(f"  - {class_count:,} characters with class data")
        print(f"  - {appearance_count:,} characters with appearance counts")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print(f"\n✓ Database connection closed")

def main():
    """Main execution."""
    # Configuration
    db_path = "fireball.db"
    json_file = "output/split/fireball_part_001_of_045.json"
    
    print("="*60)
    print("FIREBALL Dataset → SQLite Loader")
    print("="*60)
    
    # Remove existing database
    db_file = Path(db_path)
    if db_file.exists():
        print(f"\n⚠ Removing existing database: {db_path}")
        db_file.unlink()
    
    # Initialize loader
    loader = FireballDBLoader(db_path)
    
    try:
        # Connect and create schema
        loader.connect()
        loader.create_schema()
        
        # Load data
        loader.load_json_file(json_file)
        
        # Post-process character aggregates
        loader.populate_character_aggregates()
        
        # Verify integrity
        success = loader.verify_data_integrity()
        
        if success:
            print(f"\n✓ SUCCESS: Database ready at {db_path}")
            return 0
        else:
            print(f"\n⚠ WARNING: Database created but integrity issues found")
            return 1
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2
        
    finally:
        loader.close()

if __name__ == "__main__":
    sys.exit(main())
