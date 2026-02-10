#!/usr/bin/env python3
"""
Clean attack names using LM Studio LLM (qwen3-4b-dnd).
Extract the actual weapon/attack name from verbose descriptions.
"""

import sqlite3
import requests
import json
import time

def clean_attack_name_with_llm(attack_name: str, lm_studio_url: str = "http://localhost:1234/v1/chat/completions") -> tuple:
    """
    Use LLM to extract clean attack name.
    Returns (cleaned_name, confidence, reasoning)
    """
    
    prompt = f"""You are cleaning D&D combat data. Extract the actual weapon or attack name from this verbose attack name.

Original attack name: "{attack_name}"

Rules:
1. Extract ONLY the weapon/attack name (e.g., "Longsword", "Staff of Power", "Unarmed Strike")
2. Keep important modifiers if they're part of the weapon (e.g., "+1 Longsword", "Flame Tongue")
3. Remove player notes, explanations, character names in parentheses
4. Keep "2-Handed" only if it's mechanically relevant to the weapon type
5. For legendary actions, keep "Legendary Action: [Attack Name]"

Examples:
- "2-Handed Because Avrae autorolls Staff of Power extra damage" → "Staff of Power"
- "2-Handed Flame Tongue Longsword (Etri Feiro)" → "Flame Tongue Longsword"
- "Radiant Mace (Defender Only) (Avenger Celestial Spirit 1)" → "Radiant Mace"
- "Legendary Action: Blue Dragon Head: Lightning Breath" → "Legendary Action: Lightning Breath"

Respond in this exact format:
CLEANED: [cleaned attack name]
CONFIDENCE: [0-100]%
REASON: [brief explanation]"""

    try:
        response = requests.post(
            lm_studio_url,
            json={
                "model": "qwen3-4b-dnd",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 150
            },
            timeout=15
        )
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content'].strip()
            
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
                # Fallback: try to extract from response
                cleaned = answer.split('\n')[0].replace('CLEANED:', '').strip()
            
            return (cleaned, confidence, reasoning)
            
    except Exception as e:
        print(f"    ✗ LLM error: {e}")
        return (None, 0, str(e))
    
    return (None, 0, "Failed to parse LLM response")


def process_problematic_attacks(min_length: int = 40, output_file: str = "attack_cleaning_suggestions.json"):
    """
    Get all attacks above length threshold and clean them with LLM.
    """
    
    print("="*60)
    print("ATTACK NAME CLEANING WITH LLM (qwen3-4b-dnd)")
    print("="*60)
    
    # Test LM Studio connectivity
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        models = response.json()['data']
        model_ids = [m['id'] for m in models]
        print(f"\n✓ LM Studio connected")
        print(f"  Available models: {', '.join(model_ids)}")
        
        if 'qwen3-4b-dnd' not in model_ids:
            print(f"\n✗ ERROR: qwen3-4b-dnd model not loaded!")
            print(f"  Please load it in LM Studio first")
            return
    except Exception as e:
        print(f"\n✗ ERROR: Cannot connect to LM Studio: {e}")
        return
    
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
    print(f"\nProcessing with LLM (this will take ~{total*2} seconds)...\n")
    
    suggestions = []
    
    for i, (attack_id, attack_name, length) in enumerate(attacks, 1):
        print(f"[{i}/{total}] Processing: {attack_name[:60]}...")
        
        cleaned, confidence, reasoning = clean_attack_name_with_llm(attack_name)
        
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
            print(f"    → {cleaned} ({confidence}% confidence)")
        else:
            print(f"    ✗ Failed to clean")
        
        # Small delay to avoid overwhelming LM Studio
        time.sleep(0.5)
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(suggestions, f, indent=2)
    
    # Summary statistics
    successful = sum(1 for s in suggestions if s['status'] == 'success')
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
