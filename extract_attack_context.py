#!/usr/bin/env python3
"""
Extract full cross-referenced data for a specific attack name.
"""

import sqlite3
import json

def get_full_attack_context(attack_name: str, output_file: str = "attack_context.json"):
    """Get all database records related to a specific attack."""
    
    conn = sqlite3.connect('fireball.db')
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()
    
    result = {
        "attack_name": attack_name,
        "attack_record": None,
        "character_snapshots_with_attack": [],
        "actions": [],
        "characters": [],
        "related_spells": [],
        "related_effects": [],
        "spell_casts": [],
        "damage_events": []
    }
    
    # 1. Get attack record
    cursor.execute("SELECT * FROM attacks WHERE attack_name = ?", (attack_name,))
    attack = cursor.fetchone()
    if not attack:
        print(f"Attack '{attack_name}' not found!")
        conn.close()
        return
    
    result["attack_record"] = dict(attack)
    attack_id = attack['attack_id']
    
    # 2. Get all character_snapshots that have this attack
    cursor.execute("""
        SELECT cs.* 
        FROM character_snapshots cs
        JOIN character_snapshot_attacks csa ON cs.snapshot_id = csa.snapshot_id
        WHERE csa.attack_id = ?
    """, (attack_id,))
    
    snapshots = cursor.fetchall()
    action_ids = set()
    character_ids = set()
    
    for snapshot in snapshots:
        snap_dict = dict(snapshot)
        snapshot_id = snapshot['snapshot_id']
        action_ids.add(snapshot['action_id'])
        character_ids.add(snapshot['character_id'])
        
        # Get all spells for this snapshot
        cursor.execute("""
            SELECT s.spell_name
            FROM spells s
            JOIN character_snapshot_spells css ON s.spell_id = css.spell_id
            WHERE css.snapshot_id = ?
        """, (snapshot_id,))
        snap_dict['spells'] = [row['spell_name'] for row in cursor.fetchall()]
        
        # Get all attacks for this snapshot
        cursor.execute("""
            SELECT a.attack_name
            FROM attacks a
            JOIN character_snapshot_attacks csa ON a.attack_id = csa.attack_id
            WHERE csa.snapshot_id = ?
        """, (snapshot_id,))
        snap_dict['attacks'] = [row['attack_name'] for row in cursor.fetchall()]
        
        # Get all effects for this snapshot
        cursor.execute("""
            SELECT e.effect_name
            FROM effects e
            JOIN character_snapshot_effects cse ON e.effect_id = cse.effect_id
            WHERE cse.snapshot_id = ?
        """, (snapshot_id,))
        snap_dict['effects'] = [row['effect_name'] for row in cursor.fetchall()]
        
        result["character_snapshots_with_attack"].append(snap_dict)
    
    # 3. Get all actions
    for action_id in action_ids:
        cursor.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,))
        action = cursor.fetchone()
        if action:
            result["actions"].append(dict(action))
    
    # 4. Get all characters
    for character_id in character_ids:
        cursor.execute("SELECT * FROM characters WHERE character_id = ?", (character_id,))
        character = cursor.fetchone()
        if character:
            result["characters"].append(dict(character))
    
    # 5. Get spell casts for these actions
    for action_id in action_ids:
        cursor.execute("""
            SELECT sc.*, s.spell_name, c.name as caster_name
            FROM spell_casts sc
            JOIN spells s ON sc.spell_id = s.spell_id
            JOIN characters c ON sc.character_id = c.character_id
            WHERE sc.action_id = ?
        """, (action_id,))
        result["spell_casts"].extend([dict(row) for row in cursor.fetchall()])
    
    # 6. Get damage events for these actions
    for action_id in action_ids:
        cursor.execute("""
            SELECT de.*
            FROM damage_events de
            WHERE de.action_id = ?
        """, (action_id,))
        result["damage_events"].extend([dict(row) for row in cursor.fetchall()])
    
    # Write to JSON file
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✓ Extracted {len(result['character_snapshots_with_attack'])} snapshots")
    print(f"✓ Related to {len(result['actions'])} actions")
    print(f"✓ Involving {len(result['characters'])} characters")
    print(f"✓ With {len(result['spell_casts'])} spell casts")
    print(f"✓ And {len(result['damage_events'])} damage events")
    print(f"\n✓ Full context saved to: {output_file}")
    
    conn.close()
    return result

if __name__ == '__main__':
    get_full_attack_context("2-Handed Because Avrae autorolls Staff of Power extra damage")
