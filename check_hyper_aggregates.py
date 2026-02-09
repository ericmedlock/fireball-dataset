#!/usr/bin/env python3
"""Verify character aggregates in Hyper file."""
from tableauhyperapi import HyperProcess, Telemetry, Connection

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(endpoint=hp.endpoint, database='fireball.hyper') as conn:
        # Check populated fields
        result = conn.execute_list_query('''
            SELECT 
                COUNT(*) as total,
                COUNT(most_common_class) as with_class,
                COUNT(most_common_race) as with_race,
                COUNT(first_seen_action_id) as with_first_seen,
                COUNT(total_appearances) as with_appearances
            FROM "Extract"."characters"
        ''')
        
        print("Character Aggregate Field Population:")
        print(f"  Total characters: {result[0][0]:,}")
        print(f"  With class data: {result[0][1]:,}")
        print(f"  With race data: {result[0][2]:,}")
        print(f"  With first_seen: {result[0][3]:,}")
        print(f"  With appearances: {result[0][4]:,}")
        
        # Show sample data
        print("\nSample characters with aggregates:")
        result = conn.execute_list_query('''
            SELECT name, most_common_class, most_common_race, total_appearances
            FROM "Extract"."characters"
            WHERE total_appearances > 150
            ORDER BY total_appearances DESC
            LIMIT 10
        ''')
        
        for name, cls, race, count in result:
            print(f"  {name:30s} {cls or 'Unknown':15s} {race or 'Unknown':20s} {count} snapshots")
