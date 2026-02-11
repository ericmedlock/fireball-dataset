#!/usr/bin/env python3
"""
Clean non-standard classes from the SQLite database and reparse all class strings
to properly extract archetypes.
Keeps only official D&D 5e classes plus Blood Hunter (and Bloodhunter variant).
"""

import sqlite3
import re
from pathlib import Path
from typing import Tuple, Optional


def parse_class(class_text: Optional[str]) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Parse class string into primary class, level, and archetype.
    
    Primary class must always be a base class name: 'Fighter', 'Druid', 'Paladin', etc.
    Archetype is extracted into separate field: 'Champion', 'Circle of Wildfire', etc.
    """
    if not class_text or class_text == "":
        return None, None, None
        
    # Handle multiclass by taking first class
    parts = class_text.split('/')
    if parts:
        first_class = parts[0].strip()
        
        # Official D&D base classes
        base_classes = [
            'Fighter', 'Wizard', 'Rogue', 'Paladin', 'Ranger', 'Cleric',
            'Barbarian', 'Monk', 'Druid', 'Warlock', 'Sorcerer', 'Bard',
            'Artificer', 'Blood Hunter'
        ]
        
        # Try each base class in order
        for base_class in base_classes:
            # Pattern 1: "BaseClass (Archetype) Level" - e.g., "Druid (Circle of Wildfire) 5"
            paren_pattern = rf'^{base_class}\s+\(([^)]+)\)\s+(\d+)$'
            match = re.match(paren_pattern, first_class, re.IGNORECASE)
            if match:
                archetype = match.group(1).strip()
                level = int(match.group(2))
                return base_class, level, archetype
            
            # Pattern 2: "Archetype BaseClass Level" - e.g., "Champion Fighter 12"
            prefix_pattern = rf'^(.+?)\s+{base_class}\s+(\d+)$'
            match = re.match(prefix_pattern, first_class, re.IGNORECASE)
            if match:
                archetype = match.group(1).strip()
                level = int(match.group(2))
                return base_class, level, archetype
            
            # Pattern 3: "BaseClass Level" - e.g., "Fighter 12" (no archetype)
            simple_pattern = rf'^{base_class}\s+(\d+)$'
            match = re.match(simple_pattern, first_class, re.IGNORECASE)
            if match:
                level = int(match.group(1))
                return base_class, level, None
        
        # No official class found
        match = re.match(r'^([A-Za-z\s]+)\s+(\d+)$', first_class)
        if match:
            class_name = match.group(1).strip()
            level = int(match.group(2))
            return class_name, level, None
            
    return None, None, None


def clean_database():
    db_path = "fireball.db"
    
    if not Path(db_path).exists():
        print(f"Error: {db_path} not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Step 1: Reparsing all class strings to extract archetypes...")
    
    # Get all snapshots with class_text
    cursor.execute("""
        SELECT snapshot_id, class_text
        FROM character_snapshots
        WHERE class_text IS NOT NULL AND class_text != ''
    """)
    snapshots = cursor.fetchall()
    
    updated_count = 0
    for snapshot_id, class_text in snapshots:
        class_primary, class_level, class_archetype = parse_class(class_text)
        
        # Update the snapshot with properly parsed values
        cursor.execute("""
            UPDATE character_snapshots
            SET class_primary = ?, class_level = ?, class_archetype = ?
            WHERE snapshot_id = ?
        """, (class_primary, class_level, class_archetype, snapshot_id))
        updated_count += 1
    
    print(f"✓ Reparsed {updated_count} snapshots")
    
    # Show examples of archetype extraction
    cursor.execute("""
        SELECT class_text, class_primary, class_archetype
        FROM character_snapshots
        WHERE class_archetype IS NOT NULL
        LIMIT 10
    """)
    examples = cursor.fetchall()
    if examples:
        print("\nExample archetype extractions:")
        for class_text, class_primary, class_archetype in examples:
            print(f"  '{class_text}' -> class={class_primary}, archetype={class_archetype}")
    
    print("\nStep 2: Cleaning non-standard classes from database...")
    
    # First, normalize Bloodhunter to Blood Hunter
    cursor.execute("""
        UPDATE character_snapshots
        SET class_primary = 'Blood Hunter'
        WHERE class_primary = 'Bloodhunter'
    """)
    normalized = cursor.rowcount
    print(f"✓ Normalized {normalized} Bloodhunter snapshots to Blood Hunter")
    
    # Get count before deletion
    cursor.execute("SELECT COUNT(*) FROM character_snapshots")
    total_before = cursor.fetchone()[0]
    
    # Get list of non-standard classes and their counts
    cursor.execute("""
        SELECT class_primary, COUNT(*) as count
        FROM character_snapshots
        WHERE class_primary IS NOT NULL
        AND class_primary NOT IN (
            'Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Monk',
            'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard', 'Artificer', 'Blood Hunter'
        )
        GROUP BY class_primary
        ORDER BY count DESC
    """)
    non_standard = cursor.fetchall()
    
    if non_standard:
        print(f"\nRemoving {len(non_standard)} non-standard classes:")
        for class_name, count in non_standard:
            print(f"  - {class_name}: {count} snapshots")
    
    # Delete snapshots with non-standard classes
    cursor.execute("""
        DELETE FROM character_snapshots
        WHERE class_primary IS NOT NULL
        AND class_primary NOT IN (
            'Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Monk',
            'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard', 'Artificer', 'Blood Hunter'
        )
    """)
    deleted = cursor.rowcount
    print(f"\n✓ Deleted {deleted} snapshots with non-standard classes")
    
    # Get count after deletion
    cursor.execute("SELECT COUNT(*) FROM character_snapshots")
    total_after = cursor.fetchone()[0]
    
    percentage = (deleted / total_before * 100) if total_before > 0 else 0
    print(f"✓ Retained {total_after} snapshots ({100-percentage:.2f}% of data)")
    
    # Update character aggregates to reflect the changes
    print("\nStep 3: Recalculating character aggregates...")
    
    # Clear existing aggregates
    cursor.execute("""
        UPDATE characters
        SET most_common_class = NULL,
            most_common_race = NULL,
            first_seen_action_id = NULL,
            last_seen_action_id = NULL,
            total_appearances = 0
    """)
    
    # Recalculate using the same logic from load_to_sqlite.py
    cursor.execute("""
        WITH class_counts AS (
            SELECT 
                character_id,
                class_primary,
                COUNT(*) as frequency
            FROM character_snapshots
            WHERE class_primary IS NOT NULL
            GROUP BY character_id, class_primary
        ),
        most_common_classes AS (
            SELECT 
                character_id,
                class_primary as most_common_class
            FROM class_counts
            WHERE (character_id, frequency) IN (
                SELECT character_id, MAX(frequency)
                FROM class_counts
                GROUP BY character_id
            )
            GROUP BY character_id
        ),
        race_counts AS (
            SELECT 
                character_id,
                race,
                COUNT(*) as frequency
            FROM character_snapshots
            WHERE race IS NOT NULL
            GROUP BY character_id, race
        ),
        most_common_races AS (
            SELECT 
                character_id,
                race as most_common_race
            FROM race_counts
            WHERE (character_id, frequency) IN (
                SELECT character_id, MAX(frequency)
                FROM race_counts
                GROUP BY character_id
            )
            GROUP BY character_id
        ),
        action_ranges AS (
            SELECT 
                character_id,
                MIN(action_id) as first_seen,
                MAX(action_id) as last_seen,
                COUNT(*) as appearances
            FROM character_snapshots
            GROUP BY character_id
        )
        UPDATE characters
        SET 
            most_common_class = (SELECT most_common_class FROM most_common_classes WHERE most_common_classes.character_id = characters.character_id),
            most_common_race = (SELECT most_common_race FROM most_common_races WHERE most_common_races.character_id = characters.character_id),
            first_seen_action_id = (SELECT first_seen FROM action_ranges WHERE action_ranges.character_id = characters.character_id),
            last_seen_action_id = (SELECT last_seen FROM action_ranges WHERE action_ranges.character_id = characters.character_id),
            total_appearances = (SELECT appearances FROM action_ranges WHERE action_ranges.character_id = characters.character_id)
        WHERE character_id IN (SELECT character_id FROM character_snapshots)
    """)
    
    print("✓ Character aggregates recalculated")
    
    # Verify the results
    cursor.execute("""
        SELECT COUNT(DISTINCT class_primary) 
        FROM character_snapshots 
        WHERE class_primary IS NOT NULL
    """)
    class_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT class_primary, COUNT(*) as count
        FROM character_snapshots
        WHERE class_primary IS NOT NULL
        GROUP BY class_primary
        ORDER BY count DESC
    """)
    classes = cursor.fetchall()
    
    print(f"\n✓ Database now contains {class_count} unique classes:")
    for class_name, count in classes:
        print(f"  {class_name}: {count} snapshots")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Database cleaned successfully!")
    print(f"✓ {db_path} is ready for Hyper export")

if __name__ == "__main__":
    clean_database()
