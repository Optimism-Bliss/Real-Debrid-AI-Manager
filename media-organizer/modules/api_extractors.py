import re
import logging

logger = logging.getLogger(__name__)

# Note: AI APIs disabled for container environment to avoid external dependencies

def extract_show_name_regex(folder_name):
    """Extract show name using regex patterns."""
    # Start with the original name
    clean = folder_name
    
    # Remove common prefixes like [TorrentCouch.com]
    clean = re.sub(r'^\[[^\]]+\]\.?', '', clean)
    
    # Special handling for common show patterns with episode extraction
    # Family Guy patterns: "Family Guy 5x09 Road to Rupert" -> "Family Guy"
    # Also handles: "Family Guy 817 Brian & Stewie" -> "Family Guy"
    if re.search(r'Family\s*Guy', clean, re.IGNORECASE):
        return "Family Guy"
    
    # Game of Thrones patterns
    if re.search(r'Game\s*[\.\_\-\s]*of\s*[\.\_\-\s]*Thrones', clean, re.IGNORECASE):
        return "Game of Thrones"
    
    # Breaking Bad patterns
    if re.search(r'Breaking\s*[\.\_\-\s]*Bad', clean, re.IGNORECASE):
        return "Breaking Bad"
    
    # Better Call Saul patterns
    if re.search(r'Better\s*[\.\_\-\s]*Call\s*[\.\_\-\s]*Saul', clean, re.IGNORECASE):
        return "Better Call Saul"
    
    # Black Mirror patterns
    if re.search(r'Black\s*[\.\_\-\s]*Mirror', clean, re.IGNORECASE):
        return "Black Mirror"
    
    # The Boys patterns
    if re.search(r'The\s*[\.\_\-\s]*Boys', clean, re.IGNORECASE):
        return "The Boys"
    
    # House of the Dragon patterns
    if re.search(r'House\s*[\.\_\-\s]*of\s*[\.\_\-\s]*the\s*[\.\_\-\s]*Dragon', clean, re.IGNORECASE):
        return "House of the Dragon"
    
    # Friends patterns
    if re.search(r'^Friends[\.\-_\s]', clean, re.IGNORECASE):
        return "Friends"
    
    # Smallville patterns
    if re.search(r'^Smallville[\.\-_\s]', clean, re.IGNORECASE):
        return "Smallville"
    
    # How I Met Your Mother patterns
    if re.search(r'How\s*[\.\_\-\s]*I\s*[\.\_\-\s]*Met\s*[\.\_\-\s]*Your\s*[\.\_\-\s]*Mother', clean, re.IGNORECASE):
        return "How I Met Your Mother"
    
    # Modern Family patterns
    if re.search(r'Modern\s*[\.\_\-\s]*Family', clean, re.IGNORECASE):
        return "Modern Family"
    
    # KonoSuba patterns
    if re.search(r'Kono\s*[\.\_\-\s]*Suba', clean, re.IGNORECASE) or re.search(r'God\'?s\s*Blessing', clean, re.IGNORECASE):
        return "KonoSuba: God's Blessing on This Wonderful World!"
    
    # The Simpsons patterns
    if re.search(r'The\s*[\.\_\-\s]*Simpsons', clean, re.IGNORECASE):
        return "The Simpsons"
    
    # South Park patterns
    if re.search(r'South\s*[\.\_\-\s]*Park', clean, re.IGNORECASE):
        return "South Park"
    
    # Rick and Morty patterns
    if re.search(r'Rick\s*[\.\_\-\s]*and\s*[\.\_\-\s]*Morty', clean, re.IGNORECASE):
        return "Rick and Morty"
    
    # American Dad patterns
    if re.search(r'American\s*[\.\_\-\s]*Dad', clean, re.IGNORECASE):
        return "American Dad!"
    
    # The Walking Dead patterns
    if re.search(r'The\s*[\.\_\-\s]*Walking\s*[\.\_\-\s]*Dead', clean, re.IGNORECASE):
        return "The Walking Dead"
    
    # Stranger Things patterns
    if re.search(r'Stranger\s*[\.\_\-\s]*Things', clean, re.IGNORECASE):
        return "Stranger Things"
    
    # The Office patterns
    if re.search(r'The\s*[\.\_\-\s]*Office', clean, re.IGNORECASE):
        return "The Office"
    
    # Sherlock patterns
    if re.search(r'^Sherlock[\.\-_\s]', clean, re.IGNORECASE):
        return "Sherlock"
    
    # Doctor Who patterns
    if re.search(r'Doctor\s*[\.\_\-\s]*Who', clean, re.IGNORECASE):
        return "Doctor Who"
    
    # Generic extraction for other shows
    # Remove season/episode info - be more aggressive
    clean = re.sub(r'S\d+E\d+.*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'S\d{1,2}.*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\d+x\d+.*$', '', clean, flags=re.IGNORECASE).strip()  # 5x09 format
    clean = re.sub(r'Season\s+\d+.*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'Complete.*$', '', clean, flags=re.IGNORECASE).strip()
    
    # Remove year and quality info
    clean = re.sub(r'\d{4}.*$', '', clean).strip()
    clean = re.sub(r'\.(720p|1080p|2160p|4K|UHD).*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\.(BluRay|WEB-DL|REMUX|WEBRip|HDRip|BDRip).*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\.(x264|x265|H264|H265|HEVC).*$', '', clean, flags=re.IGNORECASE).strip()
    
    # Remove quality/format indicators
    clean = re.sub(r'\[[\d\.]+GB\].*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'HD\..*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\[Uncensored\].*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\[filiza\s*ru\].*$', '', clean, flags=re.IGNORECASE).strip()
    
    # Clean up separators and convert to proper title
    clean = re.sub(r'[\.\-_]+', ' ', clean).strip()
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Convert to title case for better matching
    if clean:
        clean = ' '.join(word.capitalize() for word in clean.split())
    
    return clean if clean else None

def extract_show_name(folder_name):
    """Extract show name using regex patterns only."""
    result = extract_show_name_regex(folder_name)
    if result:
        logger.info(f"Regex extracted show name: {result} from {folder_name}")
        return result
    
    logger.warning(f"Could not extract show name from: {folder_name}")
    return None

def extract_movie_name_regex(folder_name):
    """Extract movie name using regex patterns."""
    # Start with the original name
    clean = folder_name
    
    # Remove common prefixes like [site.com]
    clean = re.sub(r'^\[[^\]]+\]\.?', '', clean)
    
    # Remove year and quality info
    clean = re.sub(r'\d{4}.*$', '', clean).strip()
    clean = re.sub(r'\.(720p|1080p|2160p|4K|UHD).*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\.(BluRay|WEB-DL|REMUX|WEBRip|BDRemux|HDRip|BDRip).*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\.(x264|x265|H264|H265|HEVC|AVC).*$', '', clean, flags=re.IGNORECASE).strip()
    
    # Remove quality/format indicators
    clean = re.sub(r'\[[\d\.]+GB\].*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'HD\..*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'(PROPER|REPACK|INTERNAL|LIMITED).*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'(DV|HDR|HDR10|Atmos|TrueHD).*$', '', clean, flags=re.IGNORECASE).strip()
    
    # Clean up separators and convert to proper title
    clean = re.sub(r'[\.\-_]+', ' ', clean).strip()
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Convert to title case for better matching
    if clean:
        clean = ' '.join(word.capitalize() for word in clean.split())
    
    return clean if clean else None

def extract_movie_name(folder_name):
    """Extract movie name using regex patterns only."""
    result = extract_movie_name_regex(folder_name)
    if result:
        logger.info(f"Regex extracted movie name: {result} from {folder_name}")
        return result
    
    logger.warning(f"Could not extract movie name from: {folder_name}")
    return None 