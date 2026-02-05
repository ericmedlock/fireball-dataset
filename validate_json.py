#!/usr/bin/env python3
"""
JSON Validation Script for FIREBALL Dataset
Checks for proper JSON formatting and identifies issues
"""

import json
import sys

def validate_json_file(filepath):
    """Validate JSON file and report any issues."""
    print(f"Validating JSON file: {filepath}")
    print("=" * 60)
    
    try:
        # Check file size
        import os
        file_size = os.path.getsize(filepath)
        print(f"File size: {file_size:,} bytes ({file_size / (1024**2):.2f} MB)")
        
        # Try to load the entire JSON
        print("\nAttempting to parse JSON...")
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        print("✓ JSON is valid!")
        print(f"✓ Top-level structure: {type(data).__name__}")
        
        if isinstance(data, list):
            print(f"✓ Number of records: {len(data):,}")
            if len(data) > 0:
                print(f"✓ First record keys: {list(data[0].keys())}")
        elif isinstance(data, dict):
            print(f"✓ Top-level keys: {list(data.keys())}")
        
        # Check last few characters
        with open(filepath, 'rb') as f:
            f.seek(-100, 2)  # Go to 100 bytes before end
            tail = f.read().decode('utf-8', errors='ignore')
            print(f"\nLast 100 characters:\n{tail}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: File is valid JSON!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"\n✗ JSON PARSE ERROR at line {e.lineno}, column {e.colno}")
        print(f"✗ Error message: {e.msg}")
        print(f"✗ Position in file: {e.pos}")
        
        # Show context around error
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                start = max(0, e.pos - 200)
                end = min(len(content), e.pos + 200)
                context = content[start:end]
                
                print(f"\nContext around error position {e.pos}:")
                print("-" * 60)
                print(context)
                print("-" * 60)
        except Exception as ctx_err:
            print(f"Could not read context: {ctx_err}")
        
        return False
        
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {type(e).__name__}")
        print(f"✗ Message: {str(e)}")
        return False

def check_file_ending(filepath):
    """Check if file has proper ending brackets/braces."""
    print("\nChecking file ending...")
    try:
        with open(filepath, 'rb') as f:
            # Read last 1000 bytes
            f.seek(-min(1000, f.seek(0, 2)), 2)
            tail = f.read().decode('utf-8', errors='ignore')
            
            # Strip whitespace to see actual last character
            stripped = tail.strip()
            if stripped:
                last_char = stripped[-1]
                print(f"Last non-whitespace character: '{last_char}' (ASCII {ord(last_char)})")
                
                if last_char == ']':
                    print("✓ Ends with ] (array closing)")
                elif last_char == '}':
                    print("✓ Ends with }} (object closing)")
                else:
                    print(f"✗ WARNING: Unexpected ending character!")
                    print(f"  Expected ] or }}, found '{last_char}'")
            else:
                print("✗ WARNING: File appears to be empty or only whitespace")
                
    except Exception as e:
        print(f"✗ Error checking file ending: {e}")

if __name__ == "__main__":
    filepath = "output/fireball_data.json"
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    print("FIREBALL Dataset JSON Validator")
    print("=" * 60)
    
    # First check the ending
    check_file_ending(filepath)
    print()
    
    # Then validate full JSON
    is_valid = validate_json_file(filepath)
    
    sys.exit(0 if is_valid else 1)
