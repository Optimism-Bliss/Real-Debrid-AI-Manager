import re
import logging
from .jav_detector import is_jav_prefix
from .ai_classifier import ai_classifier
from .smart_cache import smart_cache

logger = logging.getLogger(__name__)

def is_tv_show(folder_name):
    """Check if folder contains TV show patterns (SXXEXX, SXX, or XxYY)."""
    # Check for episode patterns first (more specific)
    if re.search(r'S\d+E\d+', folder_name, re.IGNORECASE):
        logger.info(f"TV Show detected (episode pattern): {folder_name}")
        return True
    
    # Check for XxYY format (like Family Guy 817, 5x09, etc.)
    if re.search(r'\b\d{1,2}x\d{1,2}\b', folder_name, re.IGNORECASE):  # 5x09, 8x17
        logger.info(f"TV Show detected (XxYY pattern): {folder_name}")
        return True
    
    # Check for XXX format (like Family Guy 817 - 3 digits episode number)
    # But only if it contains known TV show names
    tv_show_names = [
        'Family Guy', 'Game of Thrones', 'Breaking Bad', 'Better Call Saul',
        'Black Mirror', 'The Boys', 'House of the Dragon', 'Friends',
        'Smallville', 'How I Met Your Mother', 'Modern Family', 'The Simpsons',
        'South Park', 'Rick and Morty', 'American Dad', 'Futurama',
        'KonoSuba', 'God\'s Blessing', 'The Walking Dead', 'Stranger Things',
        'The Office', 'Sherlock', 'Doctor Who', 'Westworld', 'Lost',
        'Prison Break', 'Dexter', 'True Detective', 'Fargo', 'The Crown',
        'Narcos', 'Ozark', 'The Witcher', 'Mandalorian', 'Vikings'
    ]
    
    for show_name in tv_show_names:
        if re.search(re.escape(show_name), folder_name, re.IGNORECASE):
            # Check for 3-digit episode number after show name (like Family Guy 817)
            if re.search(rf'{re.escape(show_name)}\s+\d{{3}}\b', folder_name, re.IGNORECASE):
                logger.info(f"TV Show detected (show name + 3-digit episode): {folder_name}")
                return True
            # Check for 2-digit episode number after show name (like Family Guy 23)
            elif re.search(rf'{re.escape(show_name)}\s+\d{{2}}\b', folder_name, re.IGNORECASE):
                logger.info(f"TV Show detected (show name + 2-digit episode): {folder_name}")
                return True
    
    # Check for season-only patterns (less specific but still shows)
    # S01, S02, S1, S2, etc. but avoid false positives
    if re.search(r'\.S\d{1,2}\.', folder_name, re.IGNORECASE):  # .S01. or .S1.
        logger.info(f"TV Show detected (season pattern .S##.): {folder_name}")
        return True
    if re.search(r'S\d{1,2}\.', folder_name, re.IGNORECASE):   # S01. or S1.
        logger.info(f"TV Show detected (season pattern S##.): {folder_name}")
        return True
    if re.search(r'\.S\d{1,2}[^a-zA-Z]', folder_name, re.IGNORECASE):  # .S01 followed by non-letter
        logger.info(f"TV Show detected (season pattern .S##[non-letter]): {folder_name}")
        return True
    if re.search(r'S\d{1,2}[^a-zA-Z]', folder_name, re.IGNORECASE):   # S01 followed by non-letter
        logger.info(f"TV Show detected (season pattern S##[non-letter]): {folder_name}")
        return True
    if re.search(r'Season\s+\d+', folder_name, re.IGNORECASE):  # Season 1, Season 01
        logger.info(f"TV Show detected (Season pattern): {folder_name}")
        return True
    
    # Additional patterns for common TV show formats
    if re.search(r'Complete.*Season', folder_name, re.IGNORECASE):  # Complete Season
        logger.info(f"TV Show detected (Complete Season): {folder_name}")
        return True
    if re.search(r'S\d{1,2}.*Complete', folder_name, re.IGNORECASE):  # S04 Complete
        logger.info(f"TV Show detected (S## Complete): {folder_name}")
        return True
    
    return False

def is_spam_or_ad(name):
    """Check if folder/file is spam or advertisement."""
    spam_patterns = [
        r'★+.*免费.*手游',           # ★★★...免费...手游
        r'★+.*免費.*手遊',           # Traditional Chinese version
        r'免费.*游戏',               # 免费...游戏
        r'免費.*遊戲',               # Traditional Chinese
        r'18禁.*手游',              # 18禁...手游
        r'18禁.*手遊',              # Traditional Chinese
        r'广告',                    # 广告 (advertisement)
        r'廣告',                    # Traditional Chinese
        r'推广',                    # 推广 (promotion)
        r'推廣',                    # Traditional Chinese
        r'.*\.exe$',                # Executable files
        r'.*\.msi$',                # Installer files
        r'setup.*\.exe',            # Setup executables
        r'install.*\.exe',          # Install executables
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            logger.warning(f"Spam/Ad detected: {name}")
            return True
    
    return False

def classify_folder(name, file_path=None):
    """Classify folder based on priority: Cache -> Spam Filter -> JAV -> Shows -> Movie, with AI enhancement."""
    logger.info(f"Classifying folder: {name}")
    
    # Priority 0: Check cache first
    cached_classification = smart_cache.get_cached_classification(name)
    if cached_classification:
        logger.info(f"Using cached classification for {name}: {cached_classification}")
        return cached_classification
    
    # Priority 1: Filter out spam/ads
    if is_spam_or_ad(name):
        logger.warning(f"Skipping spam/ad: {name}")
        smart_cache.cache_classification(name, 'SKIP', file_path)
        return 'SKIP'
    
    # Priority 2: Check for JAV prefix using traditional method
    if is_jav_prefix(name):
        logger.info(f"Classified as JAV (traditional): {name}")
        smart_cache.cache_classification(name, 'JAV', file_path)
        return 'JAV'
    
    # Priority 3: Check for TV show patterns
    if is_tv_show(name):
        logger.info(f"Classified as TV Show (traditional): {name}")
        smart_cache.cache_classification(name, 'Shows', file_path)
        return 'Shows'
    
    # Priority 4: Traditional classification as movie
    traditional_classification = 'Movie'
    logger.info(f"Traditional classification as Movie: {name}")
    
    # Priority 5: AI Enhancement for difficult cases
    if smart_cache.should_use_ai(name, file_path):
        logger.info(f"Using AI for difficult case: {name}")
        
        # Check if we have cached AI result
        cached_ai = smart_cache.get_cached_ai_classification(name)
        if cached_ai:
            ai_classification, confidence = cached_ai
            logger.info(f"Using cached AI classification: {ai_classification} (confidence: {confidence})")
        else:
            ai_classification, confidence = ai_classifier.classify_with_ai(name, traditional_classification)
            smart_cache.cache_ai_classification(name, ai_classification, confidence)
        
        # Only override traditional classification if AI is confident
        confidence_threshold = ai_classifier.get_confidence_threshold()
        if confidence >= confidence_threshold:
            logger.info(f"AI overrode classification: {traditional_classification} -> {ai_classification} (confidence: {confidence})")
            smart_cache.cache_classification(name, ai_classification, file_path)
            return ai_classification
        else:
            logger.info(f"AI confidence too low ({confidence} < {confidence_threshold}), keeping traditional classification: {traditional_classification}")
    
    # Cache the final classification
    smart_cache.cache_classification(name, traditional_classification, file_path)
    return traditional_classification

def learn_from_correction(folder_name: str, correct_classification: str, original_classification: str, reason: str = ""):
    """Learn from manual corrections to improve future classifications."""
    # Add to smart cache
    smart_cache.add_manual_correction(folder_name, original_classification, correct_classification, reason)
    
    # Also teach AI classifier
    ai_classifier.learn_from_correction(folder_name, correct_classification, original_classification)
    
    logger.info(f"Learned from manual correction: {folder_name} {original_classification} -> {correct_classification}")

def get_cache_stats():
    """Get cache statistics."""
    return smart_cache.get_cache_stats()

def cleanup_cache(days: int = 30):
    """Clean up old cache entries."""
    smart_cache.cleanup_old_cache(days)

def get_unapplied_corrections():
    """Get manual corrections that haven't been applied to AI learning."""
    return smart_cache.get_unapplied_corrections() 