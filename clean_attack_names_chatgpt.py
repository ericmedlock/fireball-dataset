#!/usr/bin/env python3
"""
Clean attack names using OpenAI API (ChatGPT).
Extract the actual weapon/attack name from verbose descriptions.
"""

import sqlite3
import json
import time
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def clean_attack_name_with_chatgpt(attack_name: str) -> tuple:
    """
    Use ChatGPT to extract clean attack name.
    Returns (cleaned_name, confidence, reasoning)
    """
    
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    prompt = f"""You are cleaning D&D combat data. Extract the actual weapon or attack name from this verbose attack name.

Original attack name: "{attack_name}"

Rules:
1. Extract ONLY the weapon/attack name (e.g., "Longsword", "Staff of Power", "Unarmed Strike")
2. Keep important modifiers if they're part of the weapon (e.g., "+1 Longsword", "Flame Tongue")
3. Remove player notes, explanations, character names in parentheses
4. Keep "2-Handed" only if it's mechanically important (e.g., different damage dice)
5. For legendary actions, keep "Legendary Action: [Attack Name]"
6. Remove explanatory text like "Because Avrae autorolls..."

Examples:
- "2-Handed Because Avrae autorolls Staff of Power extra damage" → "Staff of Power (2-Handed)"
- "2-Handed Flame Tongue Longsword (Etri Feiro)" → "Flame Tongue Longsword (2-Handed)"
- "Radiant Mace (Defender Only) (Avenger Celestial Spirit 1)" → "Radiant Mace"
- "Legendary Action: Blue Dragon Head: Lightning Breath" → "Legendary Action: Lightning Breath"
- "7 Book of Harmony - an arrangement of any parallel narratives which presents a single continuous narrative" → "Book of Harmony"

Respond in this exact format:
CLEANED: [cleaned attack name]
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
        cleaned = None
        confidence = 0
        reasoning = ""
        
        for line in answer.split('\n'):
            if line.startswith('CLEANED:'):
                cleaned = line.replace('CLEANED:', '').strip()
            elif line.startswith('CONFIDENCE:'):
                conf_str = line.replace('CONFIDENCE:', '').strip().replace('%', '')
                try:
                    confidence = int(conf_str)
                except:
                    confidence = 70
            elif line.startswith('REASON:'):
                reasoning = line.replace('REASON:', '').strip()
        
        if not cleaned:
            # Try to extract from first line if format not followed
            lines = answer.split('\n')
            for line in lines:
                if line and not line.startswith('CONFIDENCE') and not line.startswith('REASON'):
                    cleaned = line.strip()
                    break
        
        return (cleaned, confidence, reasoning)
            
    except Exception as e:
        print(f"    ✗ API error: {e}")
        return (None, 0, str(e))


def process_problematic_attacks(min_length: int = 40, output_file: str = "attack_cleaning_suggestions.json"):
    """
    Get all attacks above length threshold and clean them with ChatGPT.
    """
    
    print("="*60)
    print("ATTACK NAME CLEANING WITH ChatGPT")
    print("="*60)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print(f"\n✗ ERROR: OPENAI_API_KEY not set in .env file!")
        print(f"  Please add your OpenAI API key to .env")
        return
    
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    print(f"\n✓ Using OpenAI model: {model}")
    
    # Connect to database
    conn = sqlite3.connect('fireball.db')
    cursor = conn.cursor()
    
    # Get problematic attacks
    cursor.execute("""
        SELECT attack_id, attack_name, LENGTH(attack_name) as len
        FROM attacks
        WHERE LENGTH(attack_name) >= ?
        ORDER BY len DESC
    """, (min_length,))
    
    attacks = cursor.fetchall()
    total = len(attacks)
    
    print(f"\n✓ Found {total} attacks with length ≥{min_length} characters")
    print(f"\nProcessing with ChatGPT...\n")
    
    suggestions = []
    successful = 0
    
    for i, (attack_id, attack_name, length) in enumerate(attacks, 1):
        print(f"[{i}/{total}] {attack_name[:70]}...")
        
        cleaned, confidence, reasoning = clean_attack_name_with_chatgpt(attack_name)
        
        suggestion = {
            "attack_id": attack_id,
            "original_name": attack_name,
            "original_length": length,
            "cleaned_name": cleaned,
            "cleaned_length": len(cleaned) if cleaned else 0,
            "confidence": confidence,
            "reasoning": reasoning,
            "status": "success" if cleaned else "failed"
        }
        
        suggestions.append(suggestion)
        
        if cleaned:
            successful += 1
            print(f"    → {cleaned} ({confidence}% confidence)")
        else:
            print(f"    ✗ Failed to clean")
        
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
    avg_reduction = sum(s['original_length'] - s['cleaned_length'] for s in suggestions if s['cleaned_name']) / successful if successful > 0 else 0
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total attacks processed: {total}")
    print(f"Successfully cleaned:    {successful} ({successful/total*100:.1f}%)")
    print(f"High confidence (≥80%):  {high_conf} ({high_conf/total*100:.1f}%)")
    print(f"Avg length reduction:    {avg_reduction:.1f} characters")
    print(f"\n✓ Suggestions saved to: {output_file}")
    print(f"\nReview the suggestions before applying to database!")
    
    conn.close()
    return suggestions


if __name__ == '__main__':
    process_problematic_attacks(min_length=40)
