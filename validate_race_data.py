#!/usr/bin/env python3
"""
Race Data Validation - Identifies corrupt race values using heuristics + LLM fallback.

Corruption patterns found:
- Race field populated with character IDs (e.g., "wcjc3y2d8z")
- Race equals character name (e.g., "Lily" has race="Lily")
- Race field contains full character names (e.g., "Uturik "Chinchillen" Rathen")

Validation approach:
1. Heuristic rules for obvious corruption (99%+ confidence)
2. LLM validation for edge cases
3. Returns True if race is valid D&D race, False if corrupt
"""

import re
import requests
from typing import Optional, Tuple

class RaceValidator:
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1/chat/completions"):
        self.lm_studio_url = lm_studio_url
        self.llm_available = self.check_llm_availability()
        
        # Known valid D&D race patterns (partial list for heuristics)
        self.valid_race_keywords = {
            'human', 'elf', 'dwarf', 'halfling', 'gnome', 'orc', 'half-orc', 'half-elf',
            'dragonborn', 'tiefling', 'aasimar', 'genasi', 'goblin', 'hobgoblin', 'bugbear',
            'kobold', 'lizardfolk', 'tabaxi', 'kenku', 'aarakocra', 'tortle', 'firbolg',
            'goliath', 'triton', 'yuan-ti', 'changeling', 'shifter', 'warforged', 'kalashtar',
            'githyanki', 'githzerai', 'centaur', 'minotaur', 'satyr', 'fairy', 'harengon',
            'owlin', 'lineage', 'reborn', 'dhampir', 'hexblood',
            # Monsters (also valid "races" in combat data)
            'dragon', 'demon', 'devil', 'elemental', 'undead', 'skeleton', 'zombie', 'ghost',
            'vampire', 'lich', 'werewolf', 'werebear', 'celestial', 'angel', 'deva', 'planetar',
            'giant', 'ogre', 'troll', 'beholder', 'mind flayer', 'illithid', 'aboleth',
            'kraken', 'tarrasque', 'hydra', 'sphinx', 'medusa', 'gorgon', 'chimera',
            'manticore', 'wyvern', 'drake', 'pudding', 'ooze', 'slime', 'jelly', 'mold',
            'slaad', 'modron', 'inevitable', 'construct', 'golem', 'homunculus', 'animated',
            'spirit', 'specter', 'wraith', 'banshee', 'revenant', 'mummy', 'ghoul', 'wight'
        }
    
    def check_llm_availability(self) -> bool:
        """Check if LM Studio is available."""
        try:
            response = requests.get("http://localhost:1234/v1/models", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def is_valid_heuristic(self, race: Optional[str], char_name: Optional[str]) -> Tuple[Optional[bool], float]:
        """
        Apply heuristic rules to validate race field.
        Returns (is_valid, confidence) or (None, 0.0) if uncertain.
        """
        if not race or race.strip() == '':
            return (False, 1.0)  # Empty = corrupt
        
        race_lower = race.lower().strip()
        
        # Rule 1: Race equals character name = CORRUPT (99% confidence)
        if char_name and race.strip() == char_name.strip():
            # Exception: "Skeleton" as both name and race is valid (it's a monster)
            if race_lower in ['skeleton', 'zombie', 'ghost', 'spirit', 'elemental']:
                return (True, 0.95)
            return (False, 0.99)
        
        # Rule 2: Contains obvious ID patterns = CORRUPT (99% confidence)
        # Pattern: 8+ alphanumeric characters with mixed case/numbers, no spaces
        if len(race) >= 8 and not ' ' in race:
            if re.match(r'^[a-z0-9]{8,}$', race_lower):
                return (False, 0.99)
        
        # Rule 3: Contains quotes or multiple capital words = likely character name (95% confidence)
        if '"' in race or "'" in race:
            return (False, 0.95)
        
        # Rule 4: Very long (>40 chars) = likely description/notes (90% confidence)
        if len(race) > 40:
            return (False, 0.90)
        
        # Rule 5: Contains known valid race keyword = VALID (95% confidence)
        for keyword in self.valid_race_keywords:
            if keyword in race_lower:
                return (True, 0.95)
        
        # Rule 6: Starts with capital, reasonable length (5-25), contains space or dash = likely valid (80%)
        if 5 <= len(race) <= 25:
            if race[0].isupper() and (' ' in race or '-' in race or race.isalpha()):
                return (True, 0.80)
        
        # Rule 7: Short single word, capitalized = possibly valid but uncertain (60%)
        if race.isalpha() and race[0].isupper() and 3 <= len(race) <= 15:
            return (None, 0.60)  # Uncertain - needs LLM
        
        # Uncertain
        return (None, 0.0)
    
    def is_valid_llm(self, race: str, char_name: Optional[str]) -> Tuple[bool, float]:
        """
        Use LM Studio to validate race field.
        Returns (is_valid, confidence).
        """
        if not self.llm_available:
            return (True, 0.5)  # Default to valid if LLM unavailable
        
        prompt = f"""You are validating data quality for a D&D combat dataset. 

Character name: {char_name or 'Unknown'}
Race field value: "{race}"

Is this race field value a VALID D&D race/creature type, or is it CORRUPT data (like a character ID, name, or random text)?

Valid race examples: Human, Elf, Dragonborn, Fire Genasi, Protector Aasimar, Ancient Red Dragon, Skeleton, Werewolf
Corrupt examples: wcjc3y2d8z (ID), Lily (if character name is Lily), Uturik "Chinchillen" Rathen (full name)

Answer with VALID or CORRUPT, and confidence percentage.
Format: "VALID 95%" or "CORRUPT 99%"
"""
        
        try:
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": "qwen2.5-3b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                timeout=10
            )
            
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content'].strip().upper()
                
                # Parse result
                is_valid = 'VALID' in answer and 'CORRUPT' not in answer
                
                # Extract confidence
                conf_match = re.search(r'(\d+)%', answer)
                confidence = int(conf_match.group(1)) / 100.0 if conf_match else 0.7
                
                return (is_valid, confidence)
                
        except Exception as e:
            print(f"      ⚠ LLM error validating '{race}': {e}")
        
        # Fallback: assume valid if LLM fails
        return (True, 0.5)
    
    def validate(self, race: Optional[str], char_name: Optional[str] = None, 
                 use_llm: bool = True) -> Tuple[bool, float, str]:
        """
        Validate race field, return (is_valid, confidence, method).
        
        Args:
            race: Race value to validate
            char_name: Character name for cross-validation
            use_llm: Whether to use LLM for uncertain cases
        
        Returns:
            (is_valid, confidence, method) where method is 'heuristic', 'llm', or 'default'
        """
        # Try heuristics first
        is_valid, confidence = self.is_valid_heuristic(race, char_name)
        
        if is_valid is not None:
            return (is_valid, confidence, 'heuristic')
        
        # Use LLM for uncertain cases
        if use_llm and self.llm_available:
            is_valid, confidence = self.is_valid_llm(race, char_name)
            return (is_valid, confidence, 'llm')
        
        # Default: assume valid (conservative)
        return (True, 0.5, 'default')


def main():
    """Test race validation on existing database."""
    import sqlite3
    
    validator = RaceValidator()
    print(f"✓ Race Validator initialized (LLM: {validator.llm_available})")
    print("\n" + "="*60)
    print("VALIDATING RACE DATA")
    print("="*60)
    
    conn = sqlite3.connect('fireball.db')
    cursor = conn.cursor()
    
    # Get characters with potential corrupt races
    cursor.execute("""
        SELECT character_id, name, most_common_race, total_appearances
        FROM characters
        WHERE most_common_race IS NOT NULL
        AND (
            name = most_common_race
            OR LENGTH(most_common_race) > 30
            OR most_common_race GLOB '*[a-z][0-9][a-z][0-9]*'
        )
        ORDER BY total_appearances DESC
        LIMIT 20
    """)
    
    suspicious_count = 0
    corrupt_count = 0
    
    print("\nSuspicious race values:\n")
    for char_id, name, race, appearances in cursor.fetchall():
        suspicious_count += 1
        is_valid, confidence, method = validator.validate(race, name, use_llm=False)
        
        status = "✓ VALID" if is_valid else "✗ CORRUPT"
        print(f"  {status:10s} ({confidence*100:>3.0f}% {method:10s}) | {name[:30]:30s} | Race: {race[:30]}")
        
        if not is_valid and confidence >= 0.9:
            corrupt_count += 1
    
    print(f"\n✓ Found {suspicious_count} suspicious values")
    print(f"  - {corrupt_count} confirmed corrupt (≥90% confidence)")
    print(f"  - Recommend filtering during ETL")
    
    conn.close()


if __name__ == '__main__':
    main()
