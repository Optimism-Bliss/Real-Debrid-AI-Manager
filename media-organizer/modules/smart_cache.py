import json
import os
import hashlib
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from .ai_classifier import ai_classifier

logger = logging.getLogger(__name__)

class SmartCache:
    def __init__(self, cache_file: str = "/app/data/smart_cache.json"):
        self.cache_file = cache_file
        self.cache_data = self._load_cache()
        self.manual_corrections_file = "/app/data/manual_corrections.json"
        self.manual_corrections = self._load_manual_corrections()
        
    def _load_cache(self) -> Dict:
        """Load cache data from file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
        
        return {
            "processed_files": {},
            "ai_classifications": {},
            "file_hashes": {},
            "last_cleanup": str(datetime.now())
        }
    
    def _save_cache(self):
        """Save cache data to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _load_manual_corrections(self) -> Dict:
        """Load manual corrections from file."""
        try:
            if os.path.exists(self.manual_corrections_file):
                with open(self.manual_corrections_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading manual corrections: {e}")
        
        return {
            "corrections": {},
            "learning_patterns": [],
            "last_updated": str(datetime.now())
        }
    
    def _save_manual_corrections(self):
        """Save manual corrections to file."""
        try:
            with open(self.manual_corrections_file, 'w', encoding='utf-8') as f:
                json.dump(self.manual_corrections, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving manual corrections: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Generate hash for file content."""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
        
        # Fallback: use file path and modification time
        try:
            stat = os.stat(file_path)
            return hashlib.md5(f"{file_path}{stat.st_mtime}".encode()).hexdigest()
        except:
            return hashlib.md5(file_path.encode()).hexdigest()
    
    def is_file_processed(self, file_path: str) -> bool:
        """Check if file has been processed before."""
        file_hash = self.get_file_hash(file_path)
        return file_hash in self.cache_data["file_hashes"]
    
    def get_cached_item(self, folder_name: str) -> Optional[Dict]:
        """Get the entire cached dictionary for a folder."""
        return self.cache_data["processed_files"].get(folder_name)
    
    def get_cached_classification(self, folder_name: str) -> Optional[str]:
        """Get cached classification for folder."""
        item = self.get_cached_item(folder_name)
        return item.get("classification") if item else None
    
    def get_cached_ai_classification(self, folder_name: str) -> Optional[Tuple[str, float]]:
        """Get cached AI classification for folder."""
        if folder_name in self.cache_data["ai_classifications"]:
            cached = self.cache_data["ai_classifications"][folder_name]
            return cached["classification"], cached["confidence"]
        return None
    
    def cache_classification(self, folder_name: str, classification: str, file_path: Optional[str] = None, dest_path: Optional[str] = None):
        """Cache classification result, including the final destination path."""
        self.cache_data["processed_files"][folder_name] = {
            "classification": classification,
            "timestamp": str(datetime.now()),
            "file_path": file_path,
            "dest_path": dest_path  # Store the destination path
        }
        
        if file_path:
            file_hash = self.get_file_hash(file_path)
            self.cache_data["file_hashes"][file_hash] = {
                "folder_name": folder_name,
                "classification": classification,
                "timestamp": str(datetime.now())
            }
        
        self._save_cache()
        logger.info(f"Cached classification for {folder_name}: {classification}")
    
    def update_cached_item(self, folder_name: str, update_data: Dict):
        """Update specific keys for a cached folder item."""
        if folder_name in self.cache_data["processed_files"]:
            self.cache_data["processed_files"][folder_name].update(update_data)
            self._save_cache()
            logger.info(f"Updated cache for {folder_name} with {update_data}")
        else:
            logger.warning(f"Attempted to update cache for non-existent item: {folder_name}")
    
    def cache_ai_classification(self, folder_name: str, classification: str, confidence: float):
        """Cache AI classification result."""
        self.cache_data["ai_classifications"][folder_name] = {
            "classification": classification,
            "confidence": confidence,
            "timestamp": str(datetime.now())
        }
        self._save_cache()
    
    def add_manual_correction(self, folder_name: str, original_classification: str, 
                            correct_classification: str, reason: str = "",
                            correct_tmdb_id: Optional[str] = None):
        """Add manual correction and learn from it. Handles both category and metadata corrections."""
        correction = {
            "original": original_classification,
            "correct": correct_classification,
            "reason": reason,
            "timestamp": str(datetime.now()),
            "applied": False
        }

        if correct_tmdb_id:
            correction["correct_tmdb_id"] = correct_tmdb_id
        
        self.manual_corrections["corrections"][folder_name] = correction
        
        # Extract learning patterns
        learning_pattern = self._extract_learning_pattern(folder_name, original_classification, correct_classification)
        if learning_pattern:
            self.manual_corrections["learning_patterns"].append(learning_pattern)
        
        self._save_manual_corrections()
        
        # Teach AI from this correction
        ai_classifier.learn_from_correction(folder_name, correct_classification, original_classification)
        
        logger.info(f"Added manual correction: {folder_name} {original_classification} -> {correct_classification}")
    
    def _extract_learning_pattern(self, folder_name: str, original: str, correct: str) -> Optional[Dict]:
        """Extract learning pattern from manual correction."""
        pattern = {
            "folder_name": folder_name,
            "original_classification": original,
            "correct_classification": correct,
            "extracted_features": {}
        }
        
        # Extract JAV patterns
        jav_pattern = self._extract_jav_pattern(folder_name)
        if jav_pattern:
            pattern["extracted_features"]["jav_code"] = jav_pattern
        
        # Extract other features
        pattern["extracted_features"]["length"] = len(folder_name)
        pattern["extracted_features"]["has_numbers"] = any(c.isdigit() for c in folder_name)
        pattern["extracted_features"]["has_letters"] = any(c.isalpha() for c in folder_name)
        pattern["extracted_features"]["has_special_chars"] = any(c in '-_[]()' for c in folder_name)
        
        return pattern
    
    def _extract_jav_pattern(self, folder_name: str) -> Optional[str]:
        """Extract JAV pattern from folder name."""
        import re
        
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
    
    def should_use_ai(self, folder_name: str, file_path: Optional[str] = None) -> bool:
        """Determine if AI should be used for this folder."""
        # Don't use AI if file is already processed
        if file_path and self.is_file_processed(file_path):
            logger.info(f"File already processed, skipping AI: {folder_name}")
            return False
        
        # Don't use AI if we have a cached classification
        if self.get_cached_classification(folder_name):
            logger.info(f"Using cached classification, skipping AI: {folder_name}")
            return False
        
        # Check if this matches any manual correction patterns
        if self._matches_manual_correction_pattern(folder_name):
            logger.info(f"Matches manual correction pattern, using AI: {folder_name}")
            return True
        
        # Use AI classifier's decision
        return ai_classifier.should_use_ai(folder_name)
    
    def _matches_manual_correction_pattern(self, folder_name: str) -> bool:
        """Check if folder matches any manual correction patterns."""
        for pattern in self.manual_corrections["learning_patterns"]:
            if self._pattern_matches(folder_name, pattern):
                return True
        return False
    
    def _pattern_matches(self, folder_name: str, pattern: Dict) -> bool:
        """Check if folder matches a learning pattern."""
        features = pattern.get("extracted_features", {})
        
        # Check JAV code pattern
        if "jav_code" in features:
            jav_pattern = self._extract_jav_pattern(folder_name)
            if jav_pattern and jav_pattern.startswith(features["jav_code"].split('-')[0]):
                return True
        
        # Check other features
        if features.get("has_numbers") != any(c.isdigit() for c in folder_name):
            return False
        if features.get("has_letters") != any(c.isalpha() for c in folder_name):
            return False
        
        return True
    
    def get_unapplied_corrections(self) -> List[Dict]:
        """Get manual corrections that haven't been applied to AI learning."""
        unapplied = []
        for folder_name, correction in self.manual_corrections["corrections"].items():
            if not correction.get("applied", False):
                unapplied.append({
                    "folder_name": folder_name,
                    **correction
                })
        return unapplied
    
    def mark_correction_applied(self, folder_name: str):
        """Mark a manual correction as applied to AI learning."""
        if folder_name in self.manual_corrections["corrections"]:
            self.manual_corrections["corrections"][folder_name]["applied"] = True
            self._save_manual_corrections()
    
    def cleanup_old_cache(self, days: int = 30):
        """Clean up old cache entries."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = str(cutoff_date)
        
        # Clean up processed files
        old_files = []
        for folder_name, data in self.cache_data["processed_files"].items():
            if data["timestamp"] < cutoff_str:
                old_files.append(folder_name)
        
        for folder_name in old_files:
            del self.cache_data["processed_files"][folder_name]
        
        # Clean up AI classifications
        old_ai = []
        for folder_name, data in self.cache_data["ai_classifications"].items():
            if data["timestamp"] < cutoff_str:
                old_ai.append(folder_name)
        
        for folder_name in old_ai:
            del self.cache_data["ai_classifications"][folder_name]
        
        if old_files or old_ai:
            self._save_cache()
            logger.info(f"Cleaned up {len(old_files)} old processed files and {len(old_ai)} old AI classifications")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "processed_files": len(self.cache_data["processed_files"]),
            "ai_classifications": len(self.cache_data["ai_classifications"]),
            "file_hashes": len(self.cache_data["file_hashes"]),
            "manual_corrections": len(self.manual_corrections["corrections"]),
            "learning_patterns": len(self.manual_corrections["learning_patterns"])
        }

# Global instance
smart_cache = SmartCache() 