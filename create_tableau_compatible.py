#!/usr/bin/env python3
"""
Create Tableau-compatible JSON formats from the FIREBALL dataset
- Creates a smaller sample file for testing
- Creates a JSONL (newline-delimited JSON) version for better handling
"""

import json
import sys

def create_sample_file(input_file, output_file, num_records=100):
    """Create a small sample file for testing."""
    print(f"Creating sample file with {num_records} records...")
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        sample_data = data[:num_records]
        
        with open(output_file, 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        print(f"✓ Created sample file: {output_file}")
        print(f"  Records: {len(sample_data):,}")
        
        import os
        file_size = os.path.getsize(output_file)
        print(f"  Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
        
        return True
    except Exception as e:
        print(f"✗ Error creating sample: {e}")
        return False

def create_jsonl_file(input_file, output_file):
    """Create JSONL (newline-delimited JSON) version."""
    print(f"\nCreating JSONL file (one JSON object per line)...")
    print("This format is better for large datasets and streaming...")
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        with open(output_file, 'w') as f:
            for i, record in enumerate(data):
                f.write(json.dumps(record))
                f.write('\n')
                
                if (i + 1) % 10000 == 0:
                    print(f"  Processed {i + 1:,} records...")
        
        print(f"✓ Created JSONL file: {output_file}")
        print(f"  Records: {len(data):,}")
        
        import os
        file_size = os.path.getsize(output_file)
        print(f"  Size: {file_size:,} bytes ({file_size / (1024**2):.2f} MB)")
        
        return True
    except Exception as e:
        print(f"✗ Error creating JSONL: {e}")
        return False

def verify_json_structure(input_file):
    """Verify the JSON structure is Tableau-friendly."""
    print("\nVerifying structure for Tableau compatibility...")
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("✗ WARNING: Data is not an array/list")
            print("  Tableau expects an array of objects")
            return False
        
        print(f"✓ Data is an array with {len(data):,} objects")
        
        if len(data) > 0:
            first_record = data[0]
            if not isinstance(first_record, dict):
                print("✗ WARNING: First item is not an object/dict")
                return False
            
            print(f"✓ Records are objects with {len(first_record)} fields")
            
            # Check for nested structures
            nested_fields = []
            for key, value in first_record.items():
                if isinstance(value, (list, dict)):
                    nested_fields.append(key)
            
            if nested_fields:
                print(f"⚠ WARNING: Found {len(nested_fields)} nested fields:")
                for field in nested_fields[:5]:  # Show first 5
                    print(f"    - {field}")
                print("  Tableau may have trouble with deeply nested JSON")
                print("  Consider flattening these fields")
        
        return True
        
    except Exception as e:
        print(f"✗ Error verifying structure: {e}")
        return False

def create_flattened_sample(input_file, output_file, num_records=100):
    """Create a flattened version that's easier for Tableau to import."""
    print(f"\nCreating flattened sample (first {num_records} records)...")
    print("This removes nested structures for easier Tableau import...")
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        flattened_data = []
        for record in data[:num_records]:
            flat_record = {}
            for key, value in record.items():
                if isinstance(value, list):
                    # Convert lists to JSON strings
                    flat_record[key] = json.dumps(value)
                elif isinstance(value, dict):
                    # Convert dicts to JSON strings
                    flat_record[key] = json.dumps(value)
                else:
                    flat_record[key] = value
            flattened_data.append(flat_record)
        
        with open(output_file, 'w') as f:
            json.dump(flattened_data, f, indent=2)
        
        print(f"✓ Created flattened sample: {output_file}")
        
        import os
        file_size = os.path.getsize(output_file)
        print(f"  Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating flattened sample: {e}")
        return False

if __name__ == "__main__":
    input_file = "output/fireball_data.json"
    
    print("=" * 70)
    print("FIREBALL Dataset - Tableau Compatible Formats Creator")
    print("=" * 70)
    
    # Verify structure
    verify_json_structure(input_file)
    
    # Create sample file (100 records)
    print("\n" + "=" * 70)
    create_sample_file(input_file, "output/fireball_sample_100.json", 100)
    
    # Create flattened sample for easier Tableau import
    print("\n" + "=" * 70)
    create_flattened_sample(input_file, "output/fireball_flattened_sample_100.json", 100)
    
    # Optionally create JSONL (uncomment if needed - takes a while for large files)
    # print("\n" + "=" * 70)
    # create_jsonl_file(input_file, "output/fireball_data.jsonl")
    
    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("\nFiles created:")
    print("  - fireball_sample_100.json: Small sample for testing")
    print("  - fireball_flattened_sample_100.json: Flattened version for Tableau")
    print("\nFor Tableau import:")
    print("  1. Try importing the sample file first to test")
    print("  2. Use the flattened version if nested data causes issues")
    print("  3. For the full dataset, consider using a database or CSV export")
