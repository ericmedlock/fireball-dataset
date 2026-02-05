#!/usr/bin/env python3
"""
Split the FIREBALL dataset into smaller, more manageable files.
Creates multiple JSON files of approximately 50MB each.
"""

import json
import os
import math

def calculate_records_per_file(total_records, total_size_bytes, target_size_mb=50):
    """Calculate how many records per file to achieve target size."""
    target_size_bytes = target_size_mb * 1024 * 1024
    avg_bytes_per_record = total_size_bytes / total_records
    records_per_file = int(target_size_bytes / avg_bytes_per_record)
    return max(1, records_per_file)

def split_json_file(input_file, output_dir, target_size_mb=50):
    """Split a large JSON file into smaller files."""
    print("=" * 70)
    print(f"Splitting {input_file} into ~{target_size_mb}MB files")
    print("=" * 70)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the data
    print(f"\nLoading data from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    total_records = len(data)
    file_size = os.path.getsize(input_file)
    
    print(f"✓ Loaded {total_records:,} records")
    print(f"✓ Total size: {file_size:,} bytes ({file_size / (1024**2):.2f} MB)")
    
    # Calculate records per file
    records_per_file = calculate_records_per_file(total_records, file_size, target_size_mb)
    num_files = math.ceil(total_records / records_per_file)
    
    print(f"\nSplit parameters:")
    print(f"  Target size per file: {target_size_mb} MB")
    print(f"  Records per file: ~{records_per_file:,}")
    print(f"  Number of files: {num_files}")
    
    # Split and save
    print(f"\nCreating {num_files} files...")
    print("-" * 70)
    
    for i in range(num_files):
        start_idx = i * records_per_file
        end_idx = min((i + 1) * records_per_file, total_records)
        chunk = data[start_idx:end_idx]
        
        # Create filename with zero-padded number
        output_file = os.path.join(output_dir, f"fireball_part_{i+1:03d}_of_{num_files:03d}.json")
        
        # Write chunk to file
        with open(output_file, 'w') as f:
            json.dump(chunk, f, indent=2)
        
        # Get file size
        chunk_size = os.path.getsize(output_file)
        
        print(f"  [{i+1:2d}/{num_files}] {os.path.basename(output_file)}")
        print(f"         Records: {len(chunk):,} (#{start_idx:,} to #{end_idx-1:,})")
        print(f"         Size: {chunk_size:,} bytes ({chunk_size / (1024**2):.2f} MB)")
    
    print("-" * 70)
    print("\n✓ COMPLETE!")
    print(f"\nOutput files saved to: {output_dir}/")
    print(f"Total files created: {num_files}")
    
    # Calculate total output size
    total_output_size = sum(
        os.path.getsize(os.path.join(output_dir, f)) 
        for f in os.listdir(output_dir) 
        if f.startswith('fireball_part_') and f.endswith('.json')
    )
    print(f"Total output size: {total_output_size:,} bytes ({total_output_size / (1024**2):.2f} MB)")
    
    return num_files

def create_index_file(output_dir):
    """Create an index file listing all split files with metadata."""
    print("\nCreating index file...")
    
    files = sorted([f for f in os.listdir(output_dir) if f.startswith('fireball_part_') and f.endswith('.json')])
    
    index = {
        "dataset": "FIREBALL",
        "total_files": len(files),
        "files": []
    }
    
    for filename in files:
        filepath = os.path.join(output_dir, filename)
        file_size = os.path.getsize(filepath)
        
        # Load to count records
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        index["files"].append({
            "filename": filename,
            "records": len(data),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024**2), 2)
        })
    
    index_file = os.path.join(output_dir, "index.json")
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"✓ Created index file: {index_file}")

if __name__ == "__main__":
    input_file = "output/fireball_data.json"
    output_dir = "output/split"
    target_size_mb = 50
    
    print("\nFIREBALL Dataset Splitter")
    print("This will create multiple smaller JSON files for easier handling\n")
    
    # Split the file
    num_files = split_json_file(input_file, output_dir, target_size_mb)
    
    # Create index
    create_index_file(output_dir)
    
    print("\n" + "=" * 70)
    print("All files are ready for use in Tableau or other tools!")
    print("=" * 70)
