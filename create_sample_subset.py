#!/usr/bin/env python3
"""
Create a <15MB properly formatted JSON subset from fireball_part_001_of_045.json
Ensures complete records and valid JSON structure.
"""

import json
import sys

def create_sample_subset(input_file, output_file, max_size_mb=15):
    """
    Read JSON records and write complete records until size limit reached.
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file
        max_size_mb: Maximum output file size in MB
    """
    max_bytes = max_size_mb * 1024 * 1024
    
    print(f"Reading from: {input_file}")
    print(f"Target max size: {max_size_mb}MB ({max_bytes:,} bytes)")
    
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total records in source: {len(data):,}")
    
    # Collect records until we approach the size limit
    selected_records = []
    current_size = 2  # Start with [] brackets
    
    for i, record in enumerate(data):
        # Convert record to JSON and check size
        record_json = json.dumps(record, ensure_ascii=False)
        record_size = len(record_json.encode('utf-8'))
        
        # Add comma size if not first record
        if i > 0:
            record_size += 1  # comma separator
        
        # Check if adding this record would exceed limit
        if current_size + record_size > max_bytes:
            print(f"Size limit reached at record {i:,}")
            break
        
        selected_records.append(record)
        current_size += record_size
        
        # Progress indicator every 100 records
        if (i + 1) % 100 == 0:
            print(f"  Processed {i+1:,} records, current size: {current_size:,} bytes ({current_size/1024/1024:.2f}MB)")
    
    # Write the subset with proper formatting (compact to stay under size limit)
    print(f"\nWriting {len(selected_records):,} records to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write compact JSON to ensure we stay under 15MB
        json.dump(selected_records, f, ensure_ascii=False)
    
    # Verify output file size and warn if over limit
    import os
    output_size = os.path.getsize(output_file)
    if output_size > 15 * 1024 * 1024:
        print(f"⚠ Warning: File is {output_size/1024/1024:.2f}MB, attempting to reduce...")
        
        # Reduce records and try again
        reduction_factor = 0.9
        while output_size > 14.9 * 1024 * 1024 and len(selected_records) > 100:
            new_count = int(len(selected_records) * reduction_factor)
            selected_records = selected_records[:new_count]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(selected_records, f, ensure_ascii=False)
            
            output_size = os.path.getsize(output_file)
            print(f"  Reduced to {len(selected_records):,} records: {output_size/1024/1024:.2f}MB")
    
    print(f"Final output file size: {output_size:,} bytes ({output_size/1024/1024:.2f}MB)")
    print(f"Records included: {len(selected_records):,}")
    
    # Validate JSON
    print("\nValidating output JSON...")
    with open(output_file, 'r', encoding='utf-8') as f:
        validated = json.load(f)
    print(f"✓ Valid JSON with {len(validated):,} complete records")
    
    return len(selected_records), output_size

if __name__ == "__main__":
    input_path = "output/split/fireball_part_001_of_045.json"
    output_path = "output/fireball_sample_for_review.json"
    
    try:
        record_count, file_size = create_sample_subset(input_path, output_path, max_size_mb=14.5)
        print(f"\n✓ Successfully created sample file with {record_count:,} records ({file_size/1024/1024:.2f}MB)")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
