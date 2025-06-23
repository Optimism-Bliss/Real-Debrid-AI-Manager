import re
import requests
import logging
from .config import TMDB_API_KEY

logger = logging.getLogger(__name__)

def search_tmdb_movie(title):
    """Search for movie in TMDB API."""
    if not TMDB_API_KEY:
        logger.warning("TMDB API key not provided")
        return None
    
    # Manual mappings for problematic titles
    manual_mappings = {
        'konosuba': 'KonoSuba: God\'s Blessing on This Wonderful World! Legend of Crimson',
        'konosuba god\'s blessing': 'KonoSuba: God\'s Blessing on This Wonderful World! Legend of Crimson',
        'konosuba legend of crimson': 'KonoSuba: God\'s Blessing on This Wonderful World! Legend of Crimson',
    }
    
    # Check for manual mappings
    title_lower = title.lower()
    for key, mapped_title in manual_mappings.items():
        if key in title_lower:
            logger.info(f"Using manual mapping: {title} -> {mapped_title}")
            title = mapped_title
            break
    
    # Extract year if present for better search accuracy
    year_match = re.search(r'(\d{4})', title)
    year = year_match.group(1) if year_match else None
    
    # Clean title but keep year if found, preserve apostrophes
    clean_title = re.sub(r"[^\w\s\d']", ' ', title).strip()  # Keep apostrophes
    clean_title = re.sub(r'\s+', ' ', clean_title)  # Normalize spaces
    
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'query': clean_title,
        'language': 'en-US',
        'page': 1
    }
    
    # Add year parameter if found for better accuracy
    if year:
        params['year'] = year
        logger.info(f"Searching TMDB for movie: '{clean_title}' ({year})")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['results']:
            movie = data['results'][0]
            logger.info(f"Found movie on TMDB: {movie['title']} ({movie.get('release_date', 'Unknown')[:4]})")
            return {
                'id': movie['id'],
                'title': movie['title'],
                'year': movie['release_date'][:4] if movie.get('release_date') else 'Unknown'
            }
        else:
            logger.warning(f"No TMDB results found for: {clean_title}")
            
            # Try fallback with shorter title for anime/complex titles
            if len(clean_title.split()) > 5:  # If title is very long
                # Try with first few words
                short_title = ' '.join(clean_title.split()[:3])
                logger.info(f"Trying fallback search with shorter title: {short_title}")
                
                fallback_params = params.copy()
                fallback_params['query'] = short_title
                
                try:
                    fallback_response = requests.get(url, params=fallback_params, timeout=10)
                    fallback_response.raise_for_status()
                    fallback_data = fallback_response.json()
                    
                    if fallback_data['results']:
                        movie = fallback_data['results'][0]
                        logger.info(f"Found movie on TMDB (fallback): {movie['title']} ({movie.get('release_date', 'Unknown')[:4]})")
                        return {
                            'id': movie['id'],
                            'title': movie['title'],
                            'year': movie['release_date'][:4] if movie.get('release_date') else 'Unknown'
                        }
                except Exception as e:
                    logger.warning(f"Fallback search also failed: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"TMDB API request error for '{title}': {e}")
    except Exception as e:
        logger.error(f"Error searching TMDB for '{title}': {e}")
    
    return None

def search_tmdb_movie_by_id(tmdb_id):
    """Search for movie in TMDB API by its ID."""
    if not TMDB_API_KEY:
        logger.warning("TMDB API key not provided")
        return None
    
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {'api_key': TMDB_API_KEY, 'language': 'en-US'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        movie = response.json()
        logger.info(f"Found movie on TMDB by ID: {movie['title']} ({movie.get('release_date', 'Unknown')[:4]})")
        return {
            'id': movie['id'],
            'title': movie['title'],
            'year': movie['release_date'][:4] if movie.get('release_date') else 'Unknown'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"TMDB API request error for movie ID '{tmdb_id}': {e}")
    except Exception as e:
        logger.error(f"Error searching TMDB for movie ID '{tmdb_id}': {e}")
    
    return None

def search_tmdb_tv(title):
    """Search for TV show in TMDB API."""
    if not TMDB_API_KEY:
        logger.warning("TMDB API key not provided")
        return None
    
    # Extract year if present for better search accuracy
    year_match = re.search(r'(\d{4})', title)
    year = year_match.group(1) if year_match else None
    
    # Clean title but keep year if found, remove season info, preserve apostrophes
    clean_title = re.sub(r'S\d+.*$', '', title, flags=re.IGNORECASE).strip()  # Remove season info
    clean_title = re.sub(r"[^\w\s\d']", ' ', clean_title).strip()  # Keep apostrophes
    clean_title = re.sub(r'\s+', ' ', clean_title)  # Normalize spaces
    
    url = f"https://api.themoviedb.org/3/search/tv"
    params = {
        'api_key': TMDB_API_KEY,
        'query': clean_title,
        'language': 'en-US',
        'page': 1
    }
    
    # Add first_air_date_year parameter if year found for better accuracy  
    if year:
        params['first_air_date_year'] = year
        logger.info(f"Searching TMDB for TV show: '{clean_title}' ({year})")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['results']:
            show = data['results'][0]
            logger.info(f"Found TV show on TMDB: {show['name']} ({show.get('first_air_date', 'Unknown')[:4]})")
            return {
                'id': show['id'],
                'title': show['name'],
                'year': show['first_air_date'][:4] if show.get('first_air_date') else 'Unknown'
            }
        else:
            logger.warning(f"No TMDB results found for: {clean_title}")
    except requests.exceptions.RequestException as e:
        logger.error(f"TMDB API request error for '{title}': {e}")
    except Exception as e:
        logger.error(f"Error searching TMDB for '{title}': {e}")
    
    return None

def search_tmdb_tv_by_id(tmdb_id):
    """Search for TV show in TMDB API by its ID."""
    if not TMDB_API_KEY:
        logger.warning("TMDB API key not provided")
        return None
    
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
    params = {'api_key': TMDB_API_KEY, 'language': 'en-US'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        show = response.json()
        logger.info(f"Found TV show on TMDB by ID: {show['name']} ({show.get('first_air_date', 'Unknown')[:4]})")
        return {
            'id': show['id'],
            'title': show['name'],
            'year': show['first_air_date'][:4] if show.get('first_air_date') else 'Unknown'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"TMDB API request error for TV show ID '{tmdb_id}': {e}")
    except Exception as e:
        logger.error(f"Error searching TMDB for TV show ID '{tmdb_id}': {e}")
        
    return None 