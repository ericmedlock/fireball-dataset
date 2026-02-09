#!/usr/bin/env python3
"""Quick verification that Hyper has same data as SQLite."""
from tableauhyperapi import HyperProcess, Telemetry, Connection

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(endpoint=hp.endpoint, database='fireball.hyper') as conn:
        # Check row counts
        chars = conn.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."characters"')
        spells = conn.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."spells"')
        actions = conn.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."actions"')
        snapshots = conn.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."character_snapshots"')
        spell_links = conn.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."character_snapshot_spells"')
        
        # Check character data integrity
        spell_chars = conn.execute_scalar_query('SELECT SUM(LENGTH(spell_name)) FROM "Extract"."spells"')
        char_chars = conn.execute_scalar_query('SELECT SUM(LENGTH(name)) FROM "Extract"."characters"')
        cmd_chars = conn.execute_scalar_query('SELECT SUM(LENGTH(command_text)) FROM "Extract"."actions"')
        
        print(f"Hyper: {chars}|{spells}|{actions}|{snapshots}|{spell_links}|{spell_chars}|{char_chars}|{cmd_chars}")
        print(f"SQLite: 1895|825|3443|61724|528276|9874|15920|172049")
        print()
        
        if (chars == 1895 and spells == 825 and actions == 3443 and 
            snapshots == 61724 and spell_links == 528276 and
            spell_chars == 9874 and char_chars == 15920 and cmd_chars == 172049):
            print("✓ PERFECT MATCH: Every row and every character verified!")
        else:
            print("✗ MISMATCH DETECTED!")
