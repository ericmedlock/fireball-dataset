#!/usr/bin/env python3
"""
Clean race field corruption using ChatGPT.
Fix cases where race = character name, race = ID, or race = descriptive text.
"""

import sqlite3
import json
import time
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def clean_race_with_chatgpt(character_name: str, race_value: str) -> tuple:
    """
    Use ChatGPT to determine if race is valid or corrupt, and suggest fix.
    Returns (is_valid, cleaned_race, confidence, reasoning)
    """
    
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    prompt = f"""You are cleaning D&D combat data. Determine if this "race" field value is a valid D&D race/creature type, or if it's corrupt data.

Character name: "{character_name}"
Race field value: "{race_value}"

Valid race examples: Human, Elf, Dwarf, Fire Genasi, Protector Aasimar, Ancient Red Dragon, Skeleton, Werewolf, Custom Lineage
Corrupt examples: Character name, database IDs (wcjc3y2d8z), descriptive text, quotes

RULES:
1. If race = character name → CORRUPT (should be NULL unless it's a monster type like "Skeleton")
2. If race is alphanumeric hash/ID → CORRUPT (should be NULL)
3. If race has quotes or brackets with notes → CORRUPT or extract valid part
4. If race is overly descriptive → extract core race or mark CORRUPT
5. Valid races should be D&D creature types (races, monsters, subraces)

Respond in this exact format:
STATUS: [VALID or CORRUPT]
CLEANED: [If CORRUPT, suggest cleaned value or "NULL" if unrecoverable. If VALID, return original.]
CONFIDENCE: [number 0-100]%
REASON: [brief explanation]"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Parse response
        is_valid = False
        cleaned = None
        confidence = 0
        reasoning = ""
        
        for line in answer.split('\n'):
            if line.startswith('STATUS:'):
                is_valid = 'VALID' in line.upper()
            elif line.startswith('CLEANED:'):
                cleaned = line.replace('CLEANED:', '').strip()
                if cleaned.upper() == 'NULL':
                    cleaned = None
            elif line.startswith('CONFIDENCE:'):
                conf_str = line.replace('CONFIDENCE:', '').strip().replace('%', '')
                try:
                    confidence = int(conf_str)
                except:
                    confidence = 70
            elif line.startswith('REASON:'):
                reasoning = line.replace('REASON:', '').strip()
        
        return (is_valid, cleaned, confidence, reasoning)
            
    except Exception as e:
        print(f"    ✗ API error: {e}")
        return (False, None, 0, str(e))


def process_corrupt_races(output_file: str = "race_cleaning_suggestions.json"):
    """
    Find and clean corrupt race values.
    """
    
    print("="*60)
    print("RACE FIELD CLEANING WITH ChatGPT")
    print("="*60)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print(f"\n✗ ERROR: OPENAI_API_KEY not set in .env file!")
        return
    
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    print(f"\n✓ Using OpenAI model: {model}")
    
    # Connect to database
    conn = sqlite3.connect('fireball.db')
    cursor = conn.cursor()
    
    # Get suspicious race values
    cursor.execute("""
        SELECT character_id, name, most_common_race, total_appearances
        FROM characters
        WHERE most_common_race IS NOT NULL
        AND (
            -- Race = Name (excluding valid monster types)
            (name = most_common_race AND name NOT IN ('Skeleton', 'Zombie', 'Ghost', 'Spirit', 'Elemental'))
            -- Very long or has problematic patterns
            OR LENGTH(most_common_race) > 35
            OR most_common_race GLOB '*[a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9]*'
            OR most_common_race LIKE '%"%'
            OR most_common_race LIKE '%[%'
        )
        ORDER BY total_appearances DESC
    """)
    
    characters = cursor.fetchall()
    total = len(characters)
    
    print(f"\n✓ Found {total} characters with suspicious race values")
    print(f"\nProcessing with ChatGPT...\n")
    
    suggestions = []
    to_clean = 0
    to_keep = 0
    
    for i, (char_id, name, race, appearances) in enumerate(characters, 1):
        print(f"[{i}/{total}] {name[:40]} | Race: {race[:40]}...")
        
        is_valid, cleaned, confidence, reasoning = clean_race_with_chatgpt(name, race)
        
        suggestion = {
            "character_id": char_id,
            "character_name": name,
            "total_appearances": appearances,
            "original_race": race,
            "is_valid": is_valid,
            "cleaned_race": cleaned,
            "confidence": confidence,
            "reasoning": reasoning,
            "action": "keep" if is_valid else "clean"
        }
        
        suggestions.append(suggestion)
        
        if is_valid:
            to_keep += 1
            print(f"    ✓ VALID: Keep as '{race}' ({confidence}% confidence)")
        else:
            to_clean += 1
            cleaned_display = cleaned if cleaned else "NULL"
            print(f"    ✗ CORRUPT: Change to '{cleaned_display}' ({confidence}% confidence)")
        
        # Small delay to avoid rate limits
        time.sleep(0.2)
        
        # Save progress every 10 items
        if i % 10 == 0:
            with open(output_file, 'w') as f:
                json.dump(suggestions, f, indent=2)
            print(f"    ... progress saved ({i}/{total})")
    
    # Final save
    with open(output_file, 'w') as f:
        json.dump(suggestions, f, indent=2)
    
    # Summary statistics
    high_conf = sum(1 for s in suggestions if s['confidence'] >= 80)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total characters processed: {total}")
    print(f"Valid races (keep):         {to_keep} ({to_keep/total*100:.1f}%)")
    print(f"Corrupt races (clean):      {to_clean} ({to_clean/total*100:.1f}%)")
    print(f"High confidence (≥80%):     {high_conf} ({high_conf/total*100:.1f}%)")
    print(f"\n✓ Suggestions saved to: {output_file}")
    print(f"\nReview the suggestions before applying to database!")
    
    conn.close()
    return suggestions


if __name__ == '__main__':
    process_corrupt_races()
