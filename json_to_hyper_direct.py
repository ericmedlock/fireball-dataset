#!/usr/bin/env python3
"""
FIREBALL Dataset to Tableau Hyper Converter (Direct API Version)
Uses tableauhyperapi directly for better control and reliability.
Efficiently converts large JSON files (2.3GB+) to Tableau .hyper format.
"""

import sys
import subprocess
import importlib.util

# ============================================================================
# AUTO-INSTALL MISSING LIBRARIES
# ============================================================================
def check_and_install_package(package_name, import_name=None):
    """Check if a package is installed, and install it if missing."""
    import_name = import_name or package_name
    
    if importlib.util.find_spec(import_name) is None:
        print(f"📦 Installing missing package: {package_name}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "-q"])
        print(f"✓ {package_name} installed successfully")
    else:
        print(f"✓ {package_name} already installed")

# Check required packages
print("=" * 70)
print("Checking dependencies...")
print("=" * 70)
required_packages = [
    ('tableauhyperapi', 'tableauhyperapi'),
    ('ijson', 'ijson'),
    ('tqdm', 'tqdm'),
]

for package, import_name in required_packages:
    check_and_install_package(package, import_name)

print("\n" + "=" * 70)
print("All dependencies installed. Starting conversion...\n")

# ============================================================================
# IMPORT LIBRARIES
# ============================================================================
import json
import ijson
import os
from pathlib import Path
from tqdm import tqdm
from tableauhyperapi import HyperProcess, Connection, TableDefinition, \
    SqlType, Telemetry, Inserter, CreateMode, NOT_NULLABLE, NULLABLE, TableName

# ============================================================================
# FLATTENING LOGIC
# ============================================================================
def flatten_json_record(record):
    """
    Flatten a nested JSON record into a tabular format suitable for Tableau.
    
    Strategy:
    1. Keep simple scalar fields as-is
    2. Convert list/dict fields to JSON strings for preservation
    3. Handle nulls appropriately
    
    Args:
        record: Dictionary representing one JSON record
        
    Returns:
        Dictionary with flattened structure
    """
    flattened = {}
    
    for key, value in record.items():
        if value is None:
            flattened[key] = None
        elif isinstance(value, str):
            flattened[key] = value
        elif isinstance(value, (int, float, bool)):
            flattened[key] = value
        elif isinstance(value, (list, dict)):
            # Convert complex structures to JSON strings
            flattened[key] = json.dumps(value, ensure_ascii=False) if value else None
        else:
            flattened[key] = str(value)
    
    return flattened

# ============================================================================
# MEMORY-EFFICIENT JSON PARSING
# ============================================================================
def parse_large_json_chunked(json_file, chunk_size=1000):
    """
    Parse large JSON file in chunks using ijson for memory efficiency.
    
    Args:
        json_file: Path to the JSON file
        chunk_size: Number of records to yield per chunk
        
    Yields:
        List of flattened records (each chunk)
    """
    chunk = []
    
    print(f"📖 Reading JSON file: {json_file}")
    print(f"   Using streaming parser (ijson) for memory efficiency")
    
    file_size = os.path.getsize(json_file)
    print(f"   File size: {file_size / (1024**3):.2f} GB\n")
    
    with open(json_file, 'rb') as f:
        parser = ijson.items(f, 'item')
        
        for record in tqdm(parser, desc="Processing records", unit=" records"):
            flattened_record = flatten_json_record(record)
            chunk.append(flattened_record)
            
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        if chunk:
            yield chunk

# ============================================================================
# HYPER TABLE DEFINITION
# ============================================================================
def create_table_definition(sample_record, table_name="Extract"):
    """
    Create Hyper table definition from a sample record.
    
    All fields are treated as TEXT (string) since we're converting
    complex structures to JSON strings.
    
    Args:
        sample_record: Dictionary with sample data
        table_name: Name for the Hyper table
        
    Returns:
        TableDefinition object
    """
    columns = []
    
    # Define columns based on the sample record
    # All columns are TEXT type to handle JSON strings and preserve data
    for key in sorted(sample_record.keys()):
        # Use NULLABLE since some fields may have null values
        columns.append(
            TableDefinition.Column(key, SqlType.text(), NULLABLE)
        )
    
    return TableDefinition(
        table_name=TableName("Extract"),
        columns=columns
    )

# ============================================================================
# HYPER FILE EXPORT
# ============================================================================
def export_to_hyper(json_file, hyper_file, chunk_size=1000):
    """
    Export JSON data to Tableau Hyper file with memory-efficient processing.
    
    Uses tableauhyperapi directly for better control and reliability.
    
    Args:
        json_file: Input JSON file path
        hyper_file: Output Hyper file path
        chunk_size: Number of records to process at once
    """
    hyper_file = Path(hyper_file)
    
    # Remove existing hyper file if it exists
    if hyper_file.exists():
        print(f"🗑️  Removing existing file: {hyper_file}")
        hyper_file.unlink()
    
    print("=" * 70)
    print(f"Converting: {json_file}")
    print(f"Output: {hyper_file}")
    print(f"Chunk size: {chunk_size:,} records")
    print("=" * 70)
    print()
    
    # Ensure output directory exists
    hyper_file.parent.mkdir(parents=True, exist_ok=True)
    
    total_records = 0
    table_def = None
    
    # Start Hyper process
    print("🚀 Starting Hyper process...")
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        # Connect to Hyper and create database
        with Connection(endpoint=hyper.endpoint,
                       database=str(hyper_file),
                       create_mode=CreateMode.CREATE_AND_REPLACE) as connection:
            
            print("✓ Hyper connection established\n")
            
            first_chunk = True
            
            # Process JSON in chunks
            for chunk_data in parse_large_json_chunked(json_file, chunk_size):
                if first_chunk:
                    # Create table definition from first record
                    table_def = create_table_definition(chunk_data[0])
                    
                    print(f"\n📊 Creating Hyper table with {len(table_def.columns)} columns:")
                    for col in table_def.columns:
                        print(f"   - {col.name} ({col.type})")
                    print()
                    
                    # Create the table
                    connection.catalog.create_table(table_def)
                    print("✓ Table created\n")
                    first_chunk = False
                
                # Insert chunk data
                with Inserter(connection, table_def) as inserter:
                    for record in chunk_data:
                        # Create row in same order as table definition
                        row = [record.get(col.name) for col in table_def.columns]
                        inserter.add_row(row)
                    inserter.execute()
                
                total_records += len(chunk_data)
                print(f"✓ Inserted {len(chunk_data):,} records (Total: {total_records:,})")
            
            print(f"\n📝 Finalizing Hyper file...")
    
    # Get final file size
    hyper_size = hyper_file.stat().st_size
    json_size = os.path.getsize(json_file)
    
    print("\n" + "=" * 70)
    print("✅ CONVERSION COMPLETE!")
    print("=" * 70)
    print(f"Total records exported: {total_records:,}")
    print(f"Output file: {hyper_file}")
    print(f"Hyper file size: {hyper_size / (1024**2):.2f} MB")
    print(f"Original JSON size: {json_size / (1024**2):.2f} MB")
    print(f"Compression ratio: {(1 - hyper_size / json_size) * 100:.1f}%")
    print("\n📈 You can now open this file in Tableau Desktop or upload to Tableau Server!")
    print("\n💡 Tips for Tableau:")
    print("   - JSON string fields can be parsed using calculated fields")
    print("   - Use SPLIT() or JSON parsing functions for nested data")
    print("   - Consider creating extracts for better performance")

# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("\n" + "=" * 70)
        print("FIREBALL Dataset to Tableau Hyper Converter")
        print("=" * 70)
        print("\nUsage:")
        print(f"  {sys.argv[0]} <input.json> [output.hyper] [chunk_size]")
        print("\nExamples:")
        print(f"  {sys.argv[0]} output/fireball_data.json")
        print(f"  {sys.argv[0]} output/split/fireball_part_001_of_045.json")
        print(f"  {sys.argv[0]} output/fireball_data.json fireball.hyper 2000")
        print("\nArguments:")
        print("  input.json   - Input JSON file (can be 2.3GB+)")
        print("  output.hyper - Output Hyper file (default: input_name.hyper)")
        print("  chunk_size   - Records to process at once (default: 1000)")
        print("\n💡 Memory Tips:")
        print("  - 16GB+ RAM: chunk_size=5000")
        print("  - 8GB RAM: chunk_size=1000 (default)")
        print("  - 4GB RAM: chunk_size=500")
        sys.exit(1)
    
    # Parse arguments
    input_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = Path(input_file).stem + ".hyper"
    
    chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    
    # Validate input file
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Run conversion
    try:
        export_to_hyper(input_file, output_file, chunk_size)
    except KeyboardInterrupt:
        print("\n\n⚠️  Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
