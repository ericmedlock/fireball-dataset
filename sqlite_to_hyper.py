#!/usr/bin/env python3
"""
Export SQLite database to Tableau Hyper format.
Converts fireball.db → fireball.hyper for optimal Tableau performance.
"""

import sqlite3
import sys
from pathlib import Path
from tableauhyperapi import HyperProcess, Telemetry, Connection, CreateMode, \
    NOT_NULLABLE, NULLABLE, SqlType, TableDefinition, TableName, Inserter

class SQLiteToHyperConverter:
    def __init__(self, sqlite_path: str, hyper_path: str):
        self.sqlite_path = sqlite_path
        self.hyper_path = hyper_path
        self.sqlite_conn = None
        self.hyper_process = None
        self.hyper_conn = None
        
    def connect_sqlite(self):
        """Connect to SQLite database."""
        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.row_factory = sqlite3.Row  # Access columns by name
        print(f"✓ Connected to SQLite: {self.sqlite_path}")
        
    def start_hyper(self):
        """Start Hyper process and create connection."""
        self.hyper_process = HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU)
        self.hyper_conn = Connection(
            endpoint=self.hyper_process.endpoint,
            database=self.hyper_path,
            create_mode=CreateMode.CREATE_AND_REPLACE
        )
        
        # Create Extract schema
        self.hyper_conn.catalog.create_schema_if_not_exists('Extract')
        
        print(f"✓ Created Hyper file: {self.hyper_path}")
        
    def create_table_definitions(self):
        """Define Hyper table schemas matching SQLite structure."""
        
        tables = {}
        
        # Characters dimension
        tables['characters'] = TableDefinition(
            table_name=TableName('Extract', 'characters'),
            columns=[
                TableDefinition.Column('character_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('name', SqlType.text(), NOT_NULLABLE),
                TableDefinition.Column('most_common_class', SqlType.text(), NULLABLE),
                TableDefinition.Column('most_common_race', SqlType.text(), NULLABLE),
                TableDefinition.Column('controller_id', SqlType.text(), NULLABLE),
                TableDefinition.Column('first_seen_action_id', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('last_seen_action_id', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('total_appearances', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('character_type', SqlType.text(), NULLABLE),
                TableDefinition.Column('classification_confidence', SqlType.double(), NULLABLE)
            ]
        )
        
        # Spells dimension
        tables['spells'] = TableDefinition(
            table_name=TableName('Extract', 'spells'),
            columns=[
                TableDefinition.Column('spell_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('spell_name', SqlType.text(), NOT_NULLABLE)
            ]
        )
        
        # Attacks dimension
        tables['attacks'] = TableDefinition(
            table_name=TableName('Extract', 'attacks'),
            columns=[
                TableDefinition.Column('attack_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('attack_name', SqlType.text(), NOT_NULLABLE)
            ]
        )
        
        # Effects dimension
        tables['effects'] = TableDefinition(
            table_name=TableName('Extract', 'effects'),
            columns=[
                TableDefinition.Column('effect_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('effect_name', SqlType.text(), NOT_NULLABLE)
            ]
        )
        
        # Actions fact
        tables['actions'] = TableDefinition(
            table_name=TableName('Extract', 'actions'),
            columns=[
                TableDefinition.Column('action_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('speaker_id', SqlType.text(), NULLABLE),
                TableDefinition.Column('current_actor_id', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('before_state_idx', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('after_state_idx', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('command_text', SqlType.text(), NULLABLE),
                TableDefinition.Column('automation_result', SqlType.text(), NULLABLE),
                TableDefinition.Column('source_file', SqlType.text(), NULLABLE)
            ]
        )
        
        # Character snapshots fact
        tables['character_snapshots'] = TableDefinition(
            table_name=TableName('Extract', 'character_snapshots'),
            columns=[
                TableDefinition.Column('snapshot_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('action_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('character_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('snapshot_type', SqlType.text(), NOT_NULLABLE),
                TableDefinition.Column('hp_current', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('hp_max', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('hp_percentage', SqlType.double(), NULLABLE),
                TableDefinition.Column('health_status', SqlType.text(), NULLABLE),
                TableDefinition.Column('class_text', SqlType.text(), NULLABLE),
                TableDefinition.Column('class_primary', SqlType.text(), NULLABLE),
                TableDefinition.Column('class_level', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('race', SqlType.text(), NULLABLE),
                TableDefinition.Column('controller_id', SqlType.text(), NULLABLE)
            ]
        )
        
        # Spell casts fact
        tables['spell_casts'] = TableDefinition(
            table_name=TableName('Extract', 'spell_casts'),
            columns=[
                TableDefinition.Column('cast_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('action_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('character_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('spell_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('damage_dealt', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('target_count', SqlType.big_int(), NULLABLE)
            ]
        )
        
        # Damage events fact
        tables['damage_events'] = TableDefinition(
            table_name=TableName('Extract', 'damage_events'),
            columns=[
                TableDefinition.Column('event_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('action_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('attacker_id', SqlType.big_int(), NULLABLE),
                TableDefinition.Column('target_name', SqlType.text(), NOT_NULLABLE),
                TableDefinition.Column('damage_amount', SqlType.big_int(), NOT_NULLABLE)
            ]
        )
        
        # Junction tables
        tables['character_snapshot_spells'] = TableDefinition(
            table_name=TableName('Extract', 'character_snapshot_spells'),
            columns=[
                TableDefinition.Column('snapshot_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('spell_id', SqlType.big_int(), NOT_NULLABLE)
            ]
        )
        
        tables['character_snapshot_attacks'] = TableDefinition(
            table_name=TableName('Extract', 'character_snapshot_attacks'),
            columns=[
                TableDefinition.Column('snapshot_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('attack_id', SqlType.big_int(), NOT_NULLABLE)
            ]
        )
        
        tables['character_snapshot_effects'] = TableDefinition(
            table_name=TableName('Extract', 'character_snapshot_effects'),
            columns=[
                TableDefinition.Column('snapshot_id', SqlType.big_int(), NOT_NULLABLE),
                TableDefinition.Column('effect_id', SqlType.big_int(), NOT_NULLABLE)
            ]
        )
        
        return tables
        
    def transfer_table(self, table_name: str, table_def: TableDefinition):
        """Transfer data from SQLite table to Hyper table."""
        # Create table in Hyper
        self.hyper_conn.catalog.create_table(table_definition=table_def)
        print(f"  Created table: {table_name}")
        
        # Get SQLite data
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if len(rows) == 0:
            print(f"    ⚠ No data in {table_name}")
            return
        
        # Insert data into Hyper
        with Inserter(self.hyper_conn, table_def) as inserter:
            for row in rows:
                inserter.add_row(list(row))
            inserter.execute()
        
        print(f"    ✓ Transferred {len(rows):,} rows")
        
    def convert(self):
        """Main conversion process."""
        print("\n" + "="*60)
        print("SQLite → Hyper Conversion")
        print("="*60 + "\n")
        
        # Connect to sources
        self.connect_sqlite()
        self.start_hyper()
        
        # Get table definitions
        print("\nCreating Hyper schema...")
        tables = self.create_table_definitions()
        
        # Transfer each table
        print("\nTransferring data...\n")
        
        # Order matters for readability (dimensions first, then facts, then junctions)
        table_order = [
            'characters', 'spells', 'attacks', 'effects',
            'actions', 'character_snapshots', 'spell_casts', 'damage_events',
            'character_snapshot_spells', 'character_snapshot_attacks', 'character_snapshot_effects'
        ]
        
        for table_name in table_order:
            self.transfer_table(table_name, tables[table_name])
        
        print("\n✓ All tables transferred successfully")
        
    def verify_hyper(self):
        """Verify Hyper file contents."""
        print("\n" + "="*60)
        print("HYPER FILE VERIFICATION")
        print("="*60 + "\n")
        
        # Get table counts from Hyper
        table_names = [
            'characters', 'spells', 'attacks', 'effects', 'actions',
            'character_snapshots', 'spell_casts', 'damage_events',
            'character_snapshot_spells', 'character_snapshot_attacks', 'character_snapshot_effects'
        ]
        
        print("Row counts in Hyper file:\n")
        for table_name in table_names:
            result = self.hyper_conn.execute_scalar_query(
                f"SELECT COUNT(*) FROM {TableName('Extract', table_name)}"
            )
            print(f"  {table_name:30s}: {result:,} rows")
        
        # Sample query
        print("\nSample query - Top 5 characters by damage:")
        result = self.hyper_conn.execute_list_query("""
            SELECT c.name, c.most_common_class, SUM(de.damage_amount) as total_damage
            FROM "Extract"."characters" c
            JOIN "Extract"."damage_events" de ON c.character_id = de.attacker_id
            GROUP BY c.character_id, c.name, c.most_common_class
            ORDER BY total_damage DESC
            LIMIT 5
        """)
        
        for row in result:
            name, cls, dmg = row
            print(f"  {name:30s} ({cls or 'Unknown':15s}): {dmg:,} damage")
        
        print("\n✓ Hyper file verified and ready for Tableau!")
        
    def close(self):
        """Clean up connections."""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            
        if self.hyper_conn:
            self.hyper_conn.close()
            
        if self.hyper_process:
            self.hyper_process.close()
            
        print("\n✓ Connections closed")

def main():
    """Main execution."""
    sqlite_path = "fireball.db"
    hyper_path = "fireball.hyper"
    
    # Check if SQLite database exists
    if not Path(sqlite_path).exists():
        print(f"✗ ERROR: SQLite database not found: {sqlite_path}")
        return 1
    
    # Remove existing Hyper file
    hyper_file = Path(hyper_path)
    if hyper_file.exists():
        print(f"⚠ Removing existing Hyper file: {hyper_path}")
        hyper_file.unlink()
    
    # Convert
    converter = SQLiteToHyperConverter(sqlite_path, hyper_path)
    
    try:
        converter.convert()
        converter.verify_hyper()
        
        # Show file size
        file_size = Path(hyper_path).stat().st_size
        print(f"\n✓ SUCCESS: Created {hyper_path} ({file_size/1024/1024:.1f} MB)")
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2
        
    finally:
        converter.close()

if __name__ == "__main__":
    sys.exit(main())
