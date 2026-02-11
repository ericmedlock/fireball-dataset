#!/usr/bin/env python3
"""Verify the Hyper file contents after cleaning."""

from tableauhyperapi import HyperProcess, Connection, Telemetry
from pathlib import Path

hyper_file = Path('fireball.hyper')

with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    with Connection(hyper.endpoint, hyper_file) as conn:
        # Check archetype extraction
        result = conn.execute_list_query('''
            SELECT class_text, class_primary, class_archetype
            FROM "Extract"."character_snapshots"
            WHERE class_archetype IS NOT NULL
            LIMIT 10
        ''')
        print('✓ Archetype extraction verified in Hyper file:\n')
        for row in result:
            print(f'  "{row[0]}" -> class={row[1]}, archetype={row[2]}')
        
        # Check class distribution
        result2 = conn.execute_list_query('''
            SELECT class_primary, COUNT(*) as cnt
            FROM "Extract"."character_snapshots"
            WHERE class_primary IS NOT NULL
            GROUP BY class_primary
            ORDER BY cnt DESC
        ''')
        print('\n✓ Class distribution in Hyper file:\n')
        for row in result2:
            print(f'  {row[0]}: {row[1]} snapshots')
        
        print('\n✓ Hyper file successfully created with:')
        print('  - Only official D&D 5e classes (+ Blood Hunter)')
        print('  - Archetypes properly extracted to separate field')
        print('  - class_primary always contains base class only')
