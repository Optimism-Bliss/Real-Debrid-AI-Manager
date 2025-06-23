import re
import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from .config import JAV_PREFIXES

logger = logging.getLogger(__name__)

class AIClassifier:
    def __init__(self):
        self.openai_client = None
        self.learning_data_file = "/app/data/ai_learning_data.json"
        self.learning_data = self._load_learning_data()
        
        # Initialize OpenAI client if API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                import openai
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed, AI features will be disabled")
        else:
            logger.warning("OpenAI API key not found, AI features will be disabled")
    
    def _load_learning_data(self) -> Dict:
        """Load learning data from file."""
        try:
            if os.path.exists(self.learning_data_file):
                with open(self.learning_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading learning data: {e}")
        return {
            "jav_patterns": [],
            "movie_patterns": [],
            "tv_patterns": [],
            "corrections": {},
            "confidence_scores": {}
        }
    
    def _save_learning_data(self):
        """Save learning data to file."""
        try:
            with open(self.learning_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving learning data: {e}")
    
    def classify_with_ai(self, folder_name: str, original_classification: str) -> Tuple[str, float]:
        """
        Use AI to classify folder name with smart workflow:
        1. Check if it's JAV first
        2. If not JAV, check if it's Shows or Movie
        3. For Shows/Movie, provide TMDB integration hints
        
        Args:
            folder_name: Name of the folder to classify
            original_classification: Classification from traditional regex method
            
        Returns:
            Tuple of (classification, confidence_score)
        """
        if not self.openai_client:
            return original_classification, 0.5
        
        try:
            # Check if we have a cached result
            if folder_name in self.learning_data["confidence_scores"]:
                cached_result = self.learning_data["confidence_scores"][folder_name]
                logger.info(f"Using cached AI classification for {folder_name}: {cached_result}")
                return cached_result["classification"], cached_result["confidence"]
            
            # Step 1: Check if it's JAV first
            jav_result = self._check_if_jav(folder_name)
            if jav_result["is_jav"]:
                logger.info(f"AI classified as JAV: {folder_name} (confidence: {jav_result['confidence']})")
                self._cache_result(folder_name, "JAV", jav_result["confidence"], jav_result["reasoning"])
                return "JAV", jav_result["confidence"]
            
            # Step 2: If not JAV, check if it's Shows or Movie
            media_result = self._classify_shows_or_movie(folder_name)
            logger.info(f"AI classified as {media_result['classification']}: {folder_name} (confidence: {media_result['confidence']})")
            self._cache_result(folder_name, media_result["classification"], media_result["confidence"], media_result["reasoning"])
            return media_result["classification"], media_result["confidence"]
            
        except Exception as e:
            logger.error(f"Error in AI classification: {e}")
            return original_classification, 0.3
    
    def _check_if_jav(self, folder_name: str) -> Dict:
        """Check if folder is JAV content."""
        context = f"""
Folder name: "{folder_name}"

Known JAV patterns from learning data:
{json.dumps(self.learning_data["jav_patterns"][-10:], indent=2)}

Known corrections:
{json.dumps(self.learning_data["corrections"], indent=2)}

Is this Japanese Adult Video (JAV) content? Look for:
- Japanese studio codes (TYOD-190, SONE-123, FC2-PPV-123456, etc.)
- Japanese adult content indicators
- Studio prefixes followed by numbers

Respond with JSON: {{"is_jav": true/false, "confidence": 0.0-1.0, "reasoning": "explanation"}}
"""
        
        response = self.openai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a JAV content detection expert. Your task is to identify Japanese Adult Video content based on folder names."
                },
                {
                    "role": "user",
                    "content": context
                }
            ],
            temperature=0.1,
            max_tokens=150
        )
        
        return self._parse_jav_response(response.choices[0].message.content)
    
    def _classify_shows_or_movie(self, folder_name: str) -> Dict:
        """Classify as Shows or Movie with TMDB integration hints."""
        context = f"""
Folder name: "{folder_name}"

This is NOT JAV content. Please classify as either:
- Shows: TV series, episodes, seasons
- Movie: Films, movies, documentaries

For Shows, look for:
- Episode patterns (S01E01, Season 1, etc.)
- Series names
- Episode numbers

For Movies, look for:
- Movie titles
- Year indicators
- Film-related terms

Respond with JSON: {{"classification": "Shows|Movie", "confidence": 0.0-1.0, "reasoning": "explanation", "tmdb_hint": "suggested search term for TMDB API"}}
"""
        
        response = self.openai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a media classification expert. Classify content as Shows or Movie and provide TMDB search hints."
                },
                {
                    "role": "user",
                    "content": context
                }
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        return self._parse_media_response(response.choices[0].message.content)
    
    def _parse_jav_response(self, response: str) -> Dict:
        """Parse AI response for JAV detection."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "is_jav": bool(result.get("is_jav", False)),
                    "confidence": float(result.get("confidence", 0.5)),
                    "reasoning": result.get("reasoning", "")
                }
        except Exception as e:
            logger.error(f"Error parsing JAV response: {e}")
        
        # Fallback parsing
        is_jav = "JAV" in response.upper() or "JAPANESE" in response.upper()
        confidence = 0.8 if is_jav else 0.3
        
        return {
            "is_jav": is_jav,
            "confidence": confidence,
            "reasoning": response
        }
    
    def _parse_media_response(self, response: str) -> Dict:
        """Parse AI response for Shows/Movie classification."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "classification": result.get("classification", "Movie"),
                    "confidence": float(result.get("confidence", 0.5)),
                    "reasoning": result.get("reasoning", ""),
                    "tmdb_hint": result.get("tmdb_hint", "")
                }
        except Exception as e:
            logger.error(f"Error parsing media response: {e}")
        
        # Fallback parsing
        classification = "Movie"
        confidence = 0.5
        
        if "SHOW" in response.upper() or "SERIES" in response.upper() or "EPISODE" in response.upper():
            classification = "Shows"
            confidence = 0.7
        
        return {
            "classification": classification,
            "confidence": confidence,
            "reasoning": response,
            "tmdb_hint": ""
        }
    
    def _cache_result(self, folder_name: str, classification: str, confidence: float, reasoning: str = ""):
        """Cache AI classification result."""
        self.learning_data["confidence_scores"][folder_name] = {
            "classification": classification,
            "confidence": confidence,
            "reasoning": reasoning
        }
        self._save_learning_data()
    
    def learn_from_correction(self, folder_name: str, correct_classification: str, original_classification: str):
        """Learn from manual corrections to improve future classifications."""
        if original_classification != correct_classification:
            self.learning_data["corrections"][folder_name] = {
                "original": original_classification,
                "correct": correct_classification,
                "timestamp": str(os.path.getmtime(self.learning_data_file) if os.path.exists(self.learning_data_file) else 0)
            }
            
            # Extract patterns for learning
            if correct_classification == "JAV":
                jav_pattern = self._extract_jav_pattern(folder_name)
                if jav_pattern and jav_pattern not in self.learning_data["jav_patterns"]:
                    self.learning_data["jav_patterns"].append(jav_pattern)
            
            self._save_learning_data()
            logger.info(f"Learned correction: {folder_name} -> {correct_classification}")
    
    def _extract_jav_pattern(self, folder_name: str) -> Optional[str]:
        """Extract JAV pattern from folder name for learning."""
        # Look for patterns like TYOD-190, SONE-123, etc.
        pattern_match = re.search(r'([A-Z0-9]{2,6})[-_](\d{3,7})', folder_name, re.IGNORECASE)
        if pattern_match:
            prefix = pattern_match.group(1).upper()
            code = pattern_match.group(2)
            return f"{prefix}-{code}"
        
        # Look for FC2-PPV patterns
        fc2_match = re.search(r'fc2[-_]?ppv[-_]?(\d{4,7})', folder_name, re.IGNORECASE)
        if fc2_match:
            code = fc2_match.group(1)
            return f"FC2-PPV-{code}"
        
        return None
    
    def get_confidence_threshold(self) -> float:
        """Get confidence threshold for AI classification."""
        threshold_str = os.getenv('AI_CONFIDENCE_THRESHOLD', '0.7')
        if not threshold_str or threshold_str.strip() == '':
            return 0.7
        return float(threshold_str)
    
    def should_use_ai(self, folder_name: str) -> bool:
        """Determine if AI should be used for this folder."""
        if not self.openai_client:
            return False
        
        # Use AI for cases that traditional methods might miss
        suspicious_patterns = [
            r'[A-Z0-9]{2,6}[-_]\d{3,7}',  # Potential JAV codes
            r'fc2[-_]?ppv',               # FC2-PPV
            r'\d{3,7}[A-Z]{1,3}',         # Numbers followed by letters
            r'[A-Z]{2,6}\d{3,7}',         # Letters followed by numbers
            r'[A-Z]{2,6}\s+\d{3,7}',      # Letters space numbers
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, folder_name, re.IGNORECASE):
                return True
        
        return False

# Global instance
ai_classifier = AIClassifier() 