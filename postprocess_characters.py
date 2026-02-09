#!/usr/bin/env python3
"""
Post-process SQLite database to populate character aggregate fields.
Run this after loading data to calculate most_common_class, most_common_race, etc.
"""

import sqlite3
import sys
from pathlib import Path
from collections import Counter

def populate_character_aggregates(db_path: str = "fireball.db"):
    """Calculate and populate character summary statistics."""
    print("="*60)
    print("Character Aggregates Post-Processing")
    print("="*60 + "\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all characters
    cursor.execute("SELECT character_id, name FROM characters")
    characters = cursor.fetchall()
    print(f"Processing {len(characters):,} characters...\n")
    
    updated = 0
    
    for char_id, char_name in characters:
        # Get all snapshots for this character
        cursor.execute("""
            SELECT class_primary, race, action_id
            FROM character_snapshots
            WHERE character_id = ?
        """, (char_id,))
        snapshots = cursor.fetchall()
        
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
        cursor.execute("""
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
        
        if updated % 100 == 0:
            print(f"  Processed {updated}/{len(characters)} characters...")
            conn.commit()
    
    conn.commit()
    print(f"\n✓ Updated {updated:,} characters")
    
    # Verification
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60 + "\n")
    
    cursor.execute("SELECT COUNT(*) FROM characters WHERE most_common_class IS NOT NULL")
    class_count = cursor.fetchone()[0]
    print(f"Characters with class data: {class_count:,}")
    
    cursor.execute("SELECT COUNT(*) FROM characters WHERE most_common_race IS NOT NULL")
    race_count = cursor.fetchone()[0]
    print(f"Characters with race data: {race_count:,}")
    
    cursor.execute("SELECT COUNT(*) FROM characters WHERE total_appearances > 0")
    appearance_count = cursor.fetchone()[0]
    print(f"Characters with appearance data: {appearance_count:,}")
    
    # Show top characters
    print("\nTop 10 characters by appearances:")
    cursor.execute("""
        SELECT name, most_common_class, most_common_race, total_appearances
        FROM characters
        WHERE total_appearances > 0
        ORDER BY total_appearances DESC
        LIMIT 10
    """)
    for name, cls, race, count in cursor.fetchall():
        print(f"  {name:30s} {cls or 'Unknown':15s} {race or 'Unknown':20s} {count:,} snapshots")
    
    # Show class distribution
    print("\nClass distribution:")
    cursor.execute("""
        SELECT most_common_class, COUNT(*) as char_count
        FROM characters
        WHERE most_common_class IS NOT NULL
        GROUP BY most_common_class
        ORDER BY char_count DESC
        LIMIT 10
    """)
    for cls, count in cursor.fetchall():
        print(f"  {cls:20s}: {count:,} characters")
    
    conn.close()
    print("\n✓ Post-processing complete!")
    return 0

if __name__ == "__main__":
    if not Path("fireball.db").exists():
        print("✗ ERROR: fireball.db not found")
        sys.exit(1)
    
    sys.exit(populate_character_aggregates())
