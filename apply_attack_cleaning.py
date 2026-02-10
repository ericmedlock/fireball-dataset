#!/usr/bin/env python3
"""
Apply attack name cleaning suggestions to the database.
Updates attacks.attack_name based on ChatGPT analysis.
"""

import sqlite3
import json
from collections import defaultdict

def apply_attack_cleaning(suggestions_file='attack_cleaning_suggestions.json', 
                          dry_run=False):
    """
    Apply attack name cleaning suggestions from ChatGPT.
    """
    
    print("="*60)
    print("APPLYING ATTACK NAME CLEANING TO DATABASE")
    print("="*60)
    
    # Load suggestions
    with open(suggestions_file, 'r') as f:
        suggestions = json.load(f)
    
    print(f"\n✓ Loaded {len(suggestions)} suggestions")
    
    # Filter only those needing cleaning
    to_clean = [s for s in suggestions if s['confidence'] >= 80]
    
    print(f"  - {len(to_clean)} to clean (confidence ≥80%)")
    print(f"  - {len(suggestions) - len(to_clean)} skipped (low confidence)")
    
    if dry_run:
        print("\n⚠ DRY RUN MODE - No changes will be made")
    
    # Connect to database
    conn = sqlite3.connect('fireball.db')
    cursor = conn.cursor()
    
    # Track changes
    stats = defaultdict(int)
    total_char_reduction = 0
    
    print("\nProcessing changes...\n")
    
    for s in to_clean:
        attack_id = s['attack_id']
        original = s['original_name']
        cleaned = s['cleaned_name']
        confidence = s['confidence']
        char_reduction = len(original) - len(cleaned)
        
        print(f"✗ {original[:60]}")
        print(f"  → {cleaned} ({confidence}%, -{char_reduction} chars)")
        
        if not dry_run:
            # Check if cleaned name already exists
            cursor.execute("SELECT attack_id FROM attacks WHERE attack_name = ?", (cleaned,))
            existing = cursor.fetchone()
            
            if existing and existing[0] != attack_id:
                # Merge: Update references to point to existing clean attack, then delete corrupt one
                target_id = existing[0]
                print(f"    (merging with existing attack_id {target_id})")
                
                # Get all snapshots that use the corrupt attack
                cursor.execute("""
                    SELECT snapshot_id 
                    FROM character_snapshot_attacks 
                    WHERE attack_id = ?
                """, (attack_id,))
                snapshots = [row[0] for row in cursor.fetchall()]
                
                for snapshot_id in snapshots:
                    # Check if snapshot already has the target attack
                    cursor.execute("""
                        SELECT 1 FROM character_snapshot_attacks 
                        WHERE snapshot_id = ? AND attack_id = ?
                    """, (snapshot_id, target_id))
                    
                    if cursor.fetchone():
                        # Duplicate - just delete the corrupt reference
                        cursor.execute("""
                            DELETE FROM character_snapshot_attacks 
                            WHERE snapshot_id = ? AND attack_id = ?
                        """, (snapshot_id, attack_id))
                    else:
                        # No duplicate - update to point to clean attack
                        cursor.execute("""
                            UPDATE character_snapshot_attacks 
                            SET attack_id = ?
                            WHERE snapshot_id = ? AND attack_id = ?
                        """, (target_id, snapshot_id, attack_id))
                
                # Delete the corrupt attack entry
                cursor.execute("DELETE FROM attacks WHERE attack_id = ?", (attack_id,))
                stats['merged'] += 1
            else:
                # Simple rename
                cursor.execute("""
                    UPDATE attacks 
                    SET attack_name = ?
                    WHERE attack_id = ?
                """, (cleaned, attack_id))
                stats['renamed'] += 1
        
        stats['cleaned'] += 1
        total_char_reduction += char_reduction
    
    # Commit changes
    if not dry_run:
        conn.commit()
        print("\n✓ Changes committed to database")
    else:
        print("\n⚠ DRY RUN - No changes committed")
    
    # Summary
    avg_reduction = total_char_reduction / len(to_clean) if to_clean else 0
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total processed:      {len(to_clean)}")
    print(f"Attacks cleaned:      {stats['cleaned']}")
    print(f"  - Renamed:          {stats.get('renamed', 0)}")
    print(f"  - Merged:           {stats.get('merged', 0)}")
    print(f"Total chars reduced:  {total_char_reduction}")
    print(f"Avg chars reduced:    {avg_reduction:.1f}")
    print(f"Avg confidence:       {sum(s['confidence'] for s in to_clean)/len(to_clean):.1f}%")
    
    conn.close()
    
    return stats


if __name__ == '__main__':
    import sys
    
    dry_run = '--dry-run' in sys.argv
    apply_attack_cleaning(dry_run=dry_run)
