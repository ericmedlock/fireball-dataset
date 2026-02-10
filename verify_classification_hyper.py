#!/usr/bin/env python3
"""
Quick verification that character_type made it to Hyper file.
"""

from tableauhyperapi import HyperProcess, Telemetry, Connection

def verify_classification():
    """Check classification data in Hyper file."""
    
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint,
                       database='fireball.hyper') as connection:
            
            # Check character_type distribution
            print("\nCharacter Type Distribution in Hyper:")
            print("="*60)
            
            result = connection.execute_list_query("""
                SELECT character_type, COUNT(*) as count
                FROM "Extract"."characters"
                GROUP BY character_type
                ORDER BY count DESC
            """)
            
            for row in result:
                print(f"  {row[0]:15s}: {row[1]:5d} characters")
            
            print("\nSample PCs with high appearances:")
            print("="*60)
            
            result = connection.execute_list_query("""
                SELECT name, most_common_class, most_common_race, 
                       total_appearances, classification_confidence
                FROM "Extract"."characters"
                WHERE character_type = 'PC'
                ORDER BY total_appearances DESC
                LIMIT 10
            """)
            
            for row in result:
                name, cls, race, apps, conf = row
                print(f"  {name:30s} {cls or 'Unknown':15s} {race or 'Unknown':20s} "
                      f"{apps:4d} apps ({conf*100:.0f}% conf)")
            
            print("\n✓ Character classifications successfully exported to Hyper!")

if __name__ == '__main__':
    verify_classification()
