#!/usr/bin/env python3
"""
Apply race cleaning suggestions to the database.
Updates characters.most_common_race based on ChatGPT analysis.
"""

import sqlite3
import json
from collections import defaultdict

def apply_race_cleaning(suggestions_file='race_cleaning_suggestions.json', 
                        dry_run=False):
    """
    Apply race cleaning suggestions from ChatGPT.
    """
    
    print("="*60)
    print("APPLYING RACE CLEANING TO DATABASE")
    print("="*60)
    
    # Load suggestions
    with open(suggestions_file, 'r') as f:
        suggestions = json.load(f)
    
    print(f"\n✓ Loaded {len(suggestions)} suggestions")
    
    # Group by action
    to_clean = [s for s in suggestions if not s['is_valid']]
    to_keep = [s for s in suggestions if s['is_valid']]
    
    print(f"  - {len(to_clean)} to clean (NULL or simplify)")
    print(f"  - {len(to_keep)} to keep (valid races)")
    
    if dry_run:
        print("\n⚠ DRY RUN MODE - No changes will be made")
    
    # Connect to database
    conn = sqlite3.connect('fireball.db')
    cursor = conn.cursor()
    
    # Track changes
    stats = defaultdict(int)
    
    print("\nProcessing changes...\n")
    
    for s in suggestions:
        char_id = s['character_id']
        char_name = s['character_name']
        original = s['original_race']
        cleaned = s['cleaned_race']
        action = s['action']
        confidence = s['confidence']
        
        if action == 'keep':
            print(f"✓ KEEP: {char_name[:40]} | {original} ({confidence}%)")
            stats['kept'] += 1
            continue
        
        # Clean the race
        if cleaned and cleaned.strip('"\'') and cleaned.upper() != 'NULL':
            # Simplify to cleaned value
            cleaned_final = cleaned.strip('"\'')
            print(f"✗ SIMPLIFY: {char_name[:40]}")
            print(f"    {original} → {cleaned_final} ({confidence}%)")
            
            if not dry_run:
                cursor.execute("""
                    UPDATE characters 
                    SET most_common_race = ?
                    WHERE character_id = ?
                """, (cleaned_final, char_id))
            
            stats['simplified'] += 1
        else:
            # NULL the race
            print(f"✗ NULL: {char_name[:40]}")
            print(f"    {original} → NULL ({confidence}%)")
            
            if not dry_run:
                cursor.execute("""
                    UPDATE characters 
                    SET most_common_race = NULL
                    WHERE character_id = ?
                """, (char_id,))
            
            stats['nulled'] += 1
    
    # Commit changes
    if not dry_run:
        conn.commit()
        print("\n✓ Changes committed to database")
    else:
        print("\n⚠ DRY RUN - No changes committed")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total processed:  {len(suggestions)}")
    print(f"Kept valid:       {stats['kept']}")
    print(f"Simplified:       {stats['simplified']}")
    print(f"Set to NULL:      {stats['nulled']}")
    print(f"\nTotal cleaned:    {stats['simplified'] + stats['nulled']}")
    
    conn.close()
    
    return stats


if __name__ == '__main__':
    import sys
    
    dry_run = '--dry-run' in sys.argv
    apply_race_cleaning(dry_run=dry_run)
