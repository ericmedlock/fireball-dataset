#!/usr/bin/env python3
"""
FIREBALL Dataset to Tableau Hyper Converter
Efficiently converts large JSON files (2.3GB+) to Tableau .hyper format
with memory-efficient parsing and automatic dependency management.
"""

import sys
import subprocess
import importlib.util

# ============================================================================
# AUTO-INSTALL MISSING LIBRARIES
# ============================================================================
def check_and_install_package(package_name, import_name=None):
    """
    Check if a package is installed, and install it if missing.
    
    Args:
        package_name: Name of the package to install (e.g., 'pandas')
        import_name: Name used for import if different (e.g., 'tableauhyperapi')
    """
    import_name = import_name or package_name
    
    if importlib.util.find_spec(import_name) is None:
        print(f"📦 Installing missing package: {package_name}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✓ {package_name} installed successfully\n")
    else:
        print(f"✓ {package_name} already installed")

# Check and install required packages
print("=" * 70)
print("Checking dependencies...")
print("=" * 70)
required_packages = [
    ('pandas', 'pandas'),
    ('pantab', 'pantab'),
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
import pandas as pd
import pantab
from tableauhyperapi import HyperProcess, Connection, TableDefinition, SqlType, Telemetry, CreateMode
from pathlib import Path
from tqdm import tqdm
import os

# ============================================================================
# FLATTENING LOGIC
# ============================================================================
def flatten_json_record(record):
    """
    Flatten a nested JSON record into a tabular format suitable for Tableau.
    
    Strategy:
    1. Keep simple scalar fields as-is (speaker_id, commands_norm, automation_results)
    2. Convert list fields to JSON strings (before_utterances, after_utterances, etc.)
    3. Convert nested object fields to JSON strings (current_actor, caster_after, etc.)
    4. Convert deeply nested arrays of objects to JSON strings (combat_state_before/after)
    
    This approach maintains data integrity while ensuring Tableau can import the data.
    For analysis, you can use Tableau's JSON parsing functions or calculated fields.
    
    Args:
        record: Dictionary representing one JSON record
        
    Returns:
        Dictionary with flattened structure
    """
    flattened = {}
    
    for key, value in record.items():
        if value is None:
            # Keep nulls as None (pandas will convert to appropriate null type)
            flattened[key] = None
        elif isinstance(value, str):
            # Keep strings as-is
            flattened[key] = value
        elif isinstance(value, (int, float, bool)):
            # Keep scalar types as-is
            flattened[key] = value
        elif isinstance(value, list):
            # Convert lists to JSON strings
            # This handles: before_utterances, after_utterances, utterance_history,
            # combat_state_before, combat_state_after, targets_after, etc.
            flattened[key] = json.dumps(value, ensure_ascii=False) if value else None
        elif isinstance(value, dict):
            # Convert objects to JSON strings
            # This handles: current_actor, caster_after, etc.
            flattened[key] = json.dumps(value, ensure_ascii=False) if value else None
        else:
            # Fallback: convert any other type to string
            flattened[key] = str(value)
    
    return flattened

# ============================================================================
# MEMORY-EFFICIENT JSON PARSING
# ============================================================================
def parse_large_json_chunked(json_file, chunk_size=1000):
    """
    Parse large JSON file in chunks using ijson for memory efficiency.
    
    ijson is a streaming JSON parser that doesn't load the entire file into memory.
    Instead, it processes the file incrementally, yielding one item at a time.
    
    Args:
        json_file: Path to the JSON file
        chunk_size: Number of records to yield per chunk
        
    Yields:
        List of flattened records (each chunk)
    """
    chunk = []
    
    print(f"📖 Reading JSON file: {json_file}")
    print(f"   Using streaming parser (ijson) for memory efficiency")
    
    # Get file size for progress tracking
    file_size = os.path.getsize(json_file)
    print(f"   File size: {file_size / (1024**3):.2f} GB\n")
    
    with open(json_file, 'rb') as f:
        # ijson.items() iterates through array items without loading entire file
        # The 'item' prefix means we're reading items from a top-level JSON array
        parser = ijson.items(f, 'item')
        
        for record in tqdm(parser, desc="Processing records", unit=" records"):
            # Flatten the record
            flattened_record = flatten_json_record(record)
            chunk.append(flattened_record)
            
            # Yield chunk when it reaches the desired size
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        # Yield remaining records
        if chunk:
            yield chunk

# ============================================================================
# HYPER FILE EXPORT
# ============================================================================
def export_to_hyper(json_file, hyper_file, chunk_size=1000):
    """
    Export JSON data to Tableau Hyper file with memory-efficient processing.
    
    Process:
    1. Parse JSON in chunks using streaming parser
    2. Convert each chunk to pandas DataFrame
    3. Append to Hyper file incrementally
    
    This approach ensures we never load the entire 2.3GB dataset into memory.
    
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
    
    first_chunk = True
    total_records = 0
    
    # Process JSON in chunks
    for chunk_data in parse_large_json_chunked(json_file, chunk_size):
        # Convert chunk to DataFrame
        df = pd.DataFrame(chunk_data)
        
        total_records += len(df)
        
        # Write to Hyper file
        # - First chunk creates the table
        # - Subsequent chunks append to existing table
        if first_chunk:
            print(f"\n📊 Creating Hyper table with {len(df.columns)} columns:")
            for col in df.columns:
                print(f"   - {col} ({df[col].dtype})")
            print()
            
            # Create new Hyper file with first chunk
            pantab.frame_to_hyper(
                df,
                hyper_file,
                table="Extract",
                table_mode="w"  # Write mode - creates new file
            )
            print(f"✓ Created Hyper file with {len(df):,} records")
            first_chunk = False
        else:
            # Append subsequent chunks
            pantab.frame_to_hyper(
                df,
                hyper_file,
                table="Extract",
                table_mode="a"  # Append mode - adds to existing table
            )
            print(f"✓ Appended {len(df):,} records (Total: {total_records:,})")
    
    # Get final file size
    hyper_size = hyper_file.stat().st_size
    
    print("\n" + "=" * 70)
    print("✅ CONVERSION COMPLETE!")
    print("=" * 70)
    print(f"Total records exported: {total_records:,}")
    print(f"Output file: {hyper_file}")
    print(f"Hyper file size: {hyper_size / (1024**2):.2f} MB")
    print(f"Compression ratio: {(1 - hyper_size / os.path.getsize(json_file)) * 100:.1f}%")
    print("\n📈 You can now open this file in Tableau Desktop or upload to Tableau Server!")

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
        print(f"  {sys.argv[0]} output/fireball_data.json fireball.hyper")
        print(f"  {sys.argv[0]} output/fireball_data.json fireball.hyper 2000")
        print("\nArguments:")
        print("  input.json   - Input JSON file (can be 2.3GB+)")
        print("  output.hyper - Output Hyper file (default: input_name.hyper)")
        print("  chunk_size   - Records to process at once (default: 1000)")
        print("\n💡 Tips:")
        print("  - Larger chunk sizes use more memory but are faster")
        print("  - For 16GB+ RAM, try chunk_size=5000")
        print("  - For 8GB RAM, use default chunk_size=1000")
        print("  - For 4GB RAM, use chunk_size=500")
        sys.exit(1)
    
    # Parse arguments
    input_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        # Auto-generate output filename
        output_file = Path(input_file).stem + ".hyper"
    
    chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    
    # Validate input file exists
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
