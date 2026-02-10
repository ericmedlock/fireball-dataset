#!/usr/bin/env python3
"""
Classify characters as PC (Player Character), NPC, Monster, or Other.
Uses heuristics for obvious cases, LM Studio LLM for uncertain cases.
"""

import sqlite3
import re
import sys
import requests
from typing import Tuple, Optional
from pathlib import Path

class CharacterClassifier:
    def __init__(self, db_path: str = "fireball.db", lm_studio_url: str = "http://localhost:1234/v1/chat/completions"):
        self.db_path = db_path
        self.lm_studio_url = lm_studio_url
        self.conn = None
        self.cursor = None
        self.llm_available = False
        
        # Stats
        self.stats = {
            'total': 0,
            'heuristic': 0,
            'llm': 0,
            'failed': 0,
            'by_type': {}
        }
        
    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✓ Connected to database: {self.db_path}")
        
    def check_llm_availability(self):
        """Check if LM Studio is running."""
        try:
            response = requests.get("http://localhost:1234/v1/models", timeout=2)
            if response.status_code == 200:
                models = response.json().get('data', [])
                available_models = [m['id'] for m in models]
                print(f"✓ LM Studio available with models: {', '.join(available_models[:3])}")
                self.llm_available = True
                return True
        except Exception as e:
            print(f"⚠ LM Studio not available: {e}")
            print("  Will use heuristics only")
            self.llm_available = False
            return False
            
    def classify_heuristic(self, name: str, class_val: Optional[str], race: Optional[str], 
                          appearances: int, description: Optional[str]) -> Tuple[Optional[str], float]:
        """
        Apply heuristic rules to classify character.
        Returns (classification, confidence) or (None, 0.0) if uncertain.
        
        CORE ASSUMPTION: Any character with class + race + proper name in a combat 
        encounter should be PC by default (combat-ready = playable character).
        """
        
        # Rule 1: Obvious non-characters (meta/system tokens)
        if name in ['DM', 'dm', 'Map', 'map', 'Environment', 'Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5']:
            return ('Other', 1.0)
        
        # Rule 2: Coded monster names (MA1, AS3, DLoT1, SK2, WE1, etc.)
        # HIGH CONFIDENCE - abbreviation pattern indicates monster tracking system
        if re.match(r'^[A-Z]{2,4}\d+$', name):
            return ('Monster', 0.95)
        
        # Rule 3: Very short generic names (likely monsters)
        if len(name) <= 3 and name.isupper():
            return ('Monster', 0.85)
        
        # Rule 4: Monster-like names (contains spaces and numbers)
        # e.g., "Goblin 2", "Orc Warrior 1" - HIGH CONFIDENCE
        if re.search(r'\d', name) and ' ' in name:
            return ('Monster', 0.90)
        
        # Rule 5: CORE PC RULE - Has class AND race = PC
        # ASSUMPTION: If character has both class and race data, they're a playable 
        # character with a full character sheet, not an NPC or monster
        if class_val and race:
            # More appearances = higher confidence
            if appearances > 50:
                return ('PC', 0.90)
            elif appearances > 20:
                return ('PC', 0.80)
            else:
                # Even with few appearances, class+race indicates PC
                return ('PC', 0.75)
        
        # Rule 6: Has class but no race = likely still PC (race might be missing from data)
        if class_val and appearances >= 5:
            return ('PC', 0.70)
        
        # Rule 7: No class, no race, few appearances = likely monster/summon
        if not class_val and not race and appearances < 10:
            return ('Monster', 0.80)
        
        # Rule 8: Has race but no class, moderate appearances = NPC
        if race and not class_val and appearances > 10:
            return ('NPC', 0.65)
        
        # Uncertain - default to NPC for remaining edge cases
        if appearances >= 3:
            return ('NPC', 0.50)
        
        return (None, 0.0)
        
    def classify_with_llm(self, name: str, class_val: Optional[str], race: Optional[str], 
                         appearances: int, description: Optional[str]) -> Tuple[str, float]:
        """
        Use LM Studio to classify character.
        Returns (classification, confidence).
        """
        if not self.llm_available:
            return ('Unknown', 0.5)
        
        # Build context for LLM
        context = f"Name: {name}\n"
        context += f"Class: {class_val or 'Unknown'}\n"
        context += f"Race: {race or 'Unknown'}\n"
        context += f"Appearances: {appearances}\n"
        if description:
            context += f"Description: {description[:200]}\n"
        
        prompt = f"""You are analyzing D&D combat data. Classify this character as one of:
- PC (Player Character): Main adventurer, has full character sheet, active in many combats
- NPC (Non-Player Character): Named ally, quest giver, or recurring character
- Monster: Enemy, summoned creature, or generic opponent
- Other: Map markers, DM notes, or non-character entities

{context}

Based on this information, classify as: PC, NPC, Monster, or Other
Respond with ONLY the classification word (PC, NPC, Monster, or Other) and a confidence percentage.
Format: "Classification: [TYPE] (Confidence: [0-100]%)"
"""
        
        try:
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": "qwen/qwen2.5-vl-7b",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 50
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content'].strip()
                
                # Parse response
                # Looking for patterns like "PC (90%)" or "Classification: Monster (Confidence: 85%)"
                classification = None
                confidence = 0.5
                
                # Try to extract classification
                for char_type in ['PC', 'NPC', 'Monster', 'Other']:
                    if char_type in answer:
                        classification = char_type
                        break
                
                # Try to extract confidence
                conf_match = re.search(r'(\d+)%', answer)
                if conf_match:
                    confidence = int(conf_match.group(1)) / 100.0
                
                if classification:
                    return (classification, confidence)
                    
        except Exception as e:
            print(f"    ⚠ LLM error for {name}: {e}")
        
        # Fallback if LLM fails
        return ('Unknown', 0.5)
        
    def classify_character(self, char_id: int, name: str, class_val: Optional[str], 
                          race: Optional[str], appearances: int) -> Tuple[str, float]:
        """
        Classify a single character using heuristics only (skip LLM for speed).
        Returns (classification, confidence).
        """
        
        # Description not stored in our schema - set to None
        description = None
        
        # Use heuristics only
        classification, confidence = self.classify_heuristic(name, class_val, race, appearances, description)
        
        # If no confident classification, mark as Unknown
        if not classification:
            classification = 'Unknown'
            confidence = 0.0
        
        self.stats['heuristic'] += 1
        return (classification, confidence)
        
    def classify_all(self):
        """Classify all characters in the database."""
        print("\n" + "="*60)
        print("CHARACTER CLASSIFICATION")
        print("="*60 + "\n")
        
        # Get all characters
        self.cursor.execute("""
            SELECT character_id, name, most_common_class, most_common_race, total_appearances
            FROM characters
            WHERE character_type = 'Unknown' OR character_type IS NULL
            ORDER BY total_appearances DESC
        """)
        characters = self.cursor.fetchall()
        
        print(f"Characters to classify: {len(characters):,}")
        print(f"LLM available: {'Yes' if self.llm_available else 'No (heuristics only)'}\n")
        
        if len(characters) == 0:
            print("✓ All characters already classified!")
            return
        
        # Classify each character
        processed = 0
        for char_id, name, class_val, race, appearances in characters:
            self.stats['total'] += 1
            
            classification, confidence = self.classify_character(char_id, name, class_val, race, appearances)
            
            # Update database
            self.cursor.execute("""
                UPDATE characters
                SET character_type = ?,
                    classification_confidence = ?
                WHERE character_id = ?
            """, (classification, confidence, char_id))
            
            # Track stats
            self.stats['by_type'][classification] = self.stats['by_type'].get(classification, 0) + 1
            
            processed += 1
            
            # Progress updates
            if processed % 100 == 0:
                self.conn.commit()
                print(f"  Processed {processed}/{len(characters)} characters...")
            elif processed % 10 == 0 and processed <= 50:
                # Show first 50 in detail
                conf_str = f"{confidence*100:.0f}%"
                print(f"    {name:30s} → {classification:8s} ({conf_str})")
        
        self.conn.commit()
        print(f"\n✓ Classified {processed:,} characters")
        
    def show_statistics(self):
        """Display classification statistics."""
        print("\n" + "="*60)
        print("CLASSIFICATION STATISTICS")
        print("="*60 + "\n")
        
        print(f"Total classified: {self.stats['total']:,}")
        print(f"  Via heuristics: {self.stats['heuristic']:,} ({self.stats['heuristic']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"  Via LLM: {self.stats['llm']:,} ({self.stats['llm']/max(self.stats['total'],1)*100:.1f}%)")
        
        print("\nBreakdown by type:")
        for char_type, count in sorted(self.stats['by_type'].items(), key=lambda x: -x[1]):
            pct = count / max(self.stats['total'], 1) * 100
            print(f"  {char_type:12s}: {count:,} ({pct:.1f}%)")
        
        # Show sample characters by type
        print("\nSample characters by type:")
        for char_type in ['PC', 'NPC', 'Monster', 'Other']:
            self.cursor.execute("""
                SELECT name, most_common_class, most_common_race, total_appearances, classification_confidence
                FROM characters
                WHERE character_type = ?
                ORDER BY total_appearances DESC
                LIMIT 5
            """, (char_type,))
            
            results = self.cursor.fetchall()
            if results:
                print(f"\n  {char_type}:")
                for name, cls, race, apps, conf in results:
                    cls_str = cls or 'Unknown'
                    race_str = race or 'Unknown'
                    print(f"    {name:30s} {cls_str:15s} {race_str:20s} {apps:3d} appearances ({conf*100:.0f}% confidence)")
        
        # Average confidence by type
        print("\nAverage confidence by type:")
        self.cursor.execute("""
            SELECT character_type, AVG(classification_confidence), COUNT(*)
            FROM characters
            WHERE character_type IS NOT NULL
            GROUP BY character_type
            ORDER BY character_type
        """)
        for char_type, avg_conf, count in self.cursor.fetchall():
            print(f"  {char_type:12s}: {avg_conf*100:.1f}% (n={count})")
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("\n✓ Database connection closed")

def main():
    """Main execution."""
    db_path = "fireball.db"
    
    if not Path(db_path).exists():
        print(f"✗ ERROR: Database not found: {db_path}")
        return 1
    
    classifier = CharacterClassifier(db_path)
    
    try:
        classifier.connect()
        classifier.check_llm_availability()
        classifier.classify_all()
        classifier.show_statistics()
        
        print("\n✓ Classification complete!")
        print(f"  Next step: python sqlite_to_hyper.py")
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2
        
    finally:
        classifier.close()

if __name__ == "__main__":
    sys.exit(main())
