import os
import re
import logging
import shutil
from .jav_detector import extract_jav_code
from .api_extractors import extract_show_name, extract_movie_name
from .tmdb_api import search_tmdb_tv, search_tmdb_movie
from .utils import move_file_if_not_exists, copy_file_if_changed, is_file_processed, mark_file_processed
import time

logger = logging.getLogger(__name__)

def clean_filename(filename):
    """Clean filename by removing invalid characters for filesystem."""
    # Remove or replace invalid characters
    clean_name = filename
    
    # Replace problematic characters with safe alternatives
    clean_name = clean_name.replace(':', ' -')      # Colon to dash
    clean_name = clean_name.replace('|', ' -')      # Pipe to dash
    clean_name = clean_name.replace('/', ' - ')     # Forward slash
    clean_name = clean_name.replace('\\', ' - ')    # Backslash
    clean_name = clean_name.replace('<', '(')       # Less than
    clean_name = clean_name.replace('>', ')')       # Greater than
    clean_name = clean_name.replace('"', "'")       # Double quote to single
    clean_name = clean_name.replace('?', '')        # Question mark
    clean_name = clean_name.replace('*', '')        # Asterisk
    
    # Clean up multiple spaces and trim
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    
    return clean_name

def process_jav_files(jav_folders, unorganized_dir, dest_dirs, tracking_data):
    """Process JAV files and copy them to appropriate folders."""
    copied_files = 0
    
    for folder_name in jav_folders:
        src_folder = os.path.join(unorganized_dir, folder_name)
        jav_code = extract_jav_code(folder_name)
        
        if jav_code:
            jav_folder_name = jav_code
            jav_filename = f"{jav_code}.strm"
        else:
            clean_name = re.sub(r'[\.\-_\s]+', '-', folder_name).strip()
            fallback_match = re.search(r'([A-Z0-9]{2,6})[\s\-_]*(\d{3,5})', clean_name, re.IGNORECASE)
            if fallback_match:
                prefix = fallback_match.group(1).upper()
                code = fallback_match.group(2)
                jav_folder_name = f"{prefix}-{code}"
                jav_filename = f"{prefix}-{code}.strm"
            else:
                jav_folder_name = clean_name
                jav_filename = f"{clean_name}.strm"
        
        jav_dest_folder = os.path.join(dest_dirs['JAV'], jav_folder_name)
        
        for file in os.listdir(src_folder):
            if file.endswith('.strm'):
                src_file = os.path.join(src_folder, file)
                dest_file = os.path.join(jav_dest_folder, jav_filename)
                
                # Check if file has been processed before
                if is_file_processed(src_file, tracking_data):
                    logger.debug(f"Skipped JAV (already processed): {folder_name}/{file}")
                    copied_files += 1
                    continue
                
                if copy_file_if_changed(src_file, dest_file):
                    logger.info(f"Copied JAV: {folder_name}/{file} -> {jav_filename}")
                    mark_file_processed(src_file, tracking_data)
                    copied_files += 1
                else:
                    logger.info(f"Skipped JAV (unchanged): {folder_name}/{file}")
                    copied_files += 1
    
    return copied_files

def process_tv_shows(tv_shows_dict, unorganized_dir, dest_dirs, tracking_data):
    """Process TV show files and copy them to appropriate folders."""
    copied_files = 0
    
    for show_name, folders in tv_shows_dict.items():
        logger.info(f"Processing show: {show_name}")
        tmdb_info = search_tmdb_tv(show_name)
        if tmdb_info:
            show_folder_name = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}) {{tmdb-{tmdb_info['id']}}}")
            clean_show_name = clean_filename(tmdb_info['title'])
        else:
            show_folder_name = clean_filename(show_name)
            clean_show_name = clean_filename(show_name)
        
        show_dest_folder = os.path.join(dest_dirs['Shows'], show_folder_name)
        
        for folder_name in folders:
            logger.info(f"Processing folder: {folder_name}")
            src_folder = os.path.join(unorganized_dir, folder_name)
            
            # Extract season info
            season_episode_match = re.search(r'S(\d+)E(\d+)', folder_name, re.IGNORECASE)
            season_only_match = re.search(r'S(\d+)', folder_name, re.IGNORECASE)
            
            # Special handling for show-specific episode formats
            if 'family guy' in folder_name.lower():
                # Family Guy XXX format (like 817 = S08E17)
                family_guy_3digit = re.search(r'Family\s+Guy\s+(\d{3})', folder_name, re.IGNORECASE)
                if family_guy_3digit:
                    episode_num = family_guy_3digit.group(1)
                    season_num = int(episode_num[0])  # First digit = season
                    ep_num = int(episode_num[1:])     # Last 2 digits = episode
                    logger.info(f"Family Guy 3-digit format: {episode_num} = S{season_num:02d}E{ep_num:02d}")
                    season_episode_match = type('Match', (), {
                        'group': lambda self, x: season_num if x == 1 else ep_num
                    })()
                # Family Guy XX format (like 23 = S02E03 or S01E23 depending on context)
                elif re.search(r'Family\s+Guy\s+(\d{2})\b', folder_name, re.IGNORECASE):
                    family_guy_2digit = re.search(r'Family\s+Guy\s+(\d{2})', folder_name, re.IGNORECASE)
                    episode_num = family_guy_2digit.group(1)
                    ep_int = int(episode_num)
                    # Logic: if <= 25, assume it's episode number in season 1
                    # if > 25, assume it's season+episode format
                    if ep_int <= 25:
                        season_num = 1
                        ep_num = ep_int
                    else:
                        season_num = int(episode_num[0])
                        ep_num = int(episode_num[1:])
                    logger.info(f"Family Guy 2-digit format: {episode_num} = S{season_num:02d}E{ep_num:02d}")
                    season_episode_match = type('Match', (), {
                        'group': lambda self, x: season_num if x == 1 else ep_num
                    })()
            
            # Check for XxYY format (5x09, 8x17)
            x_format_match = re.search(r'(\d{1,2})x(\d{1,2})', folder_name, re.IGNORECASE)
            if x_format_match:
                season_num = int(x_format_match.group(1))
                ep_num = int(x_format_match.group(2))
                logger.info(f"XxYY format detected: {season_num}x{ep_num} = S{season_num:02d}E{ep_num:02d}")
                # Create fake match object for consistent processing
                season_episode_match = type('Match', (), {
                    'group': lambda self, x: season_num if x == 1 else ep_num
                })()
            
            if season_episode_match:
                # Episode format: S01E01 - keep individual episode
                season_num = int(season_episode_match.group(1))
                episode_num = int(season_episode_match.group(2))
                season_folder = f"Season {season_num:02d}"
                episode_filename = f"{clean_show_name} S{season_num:02d}E{episode_num:02d}.strm"
            elif season_only_match:
                # Season-only format: S01 - assign sequential episode numbers
                current_season_num = int(season_only_match.group(1))
                season_folder = f"Season {current_season_num:02d}"
                
                # Use sequential episode numbering for season-only folders
                episode_filename = f"{clean_show_name} S{current_season_num:02d}E01.strm"
            else:
                # Fallback: put in root show folder with unique name
                season_folder = ""
                episode_filename = f"{clean_show_name} E01.strm"
            
            # Create season subfolder if needed
            if season_folder:
                episode_dest_folder = os.path.join(show_dest_folder, season_folder)
            else:
                episode_dest_folder = show_dest_folder
            
            # Check if individual files have episode numbers
            files_in_folder = [f for f in os.listdir(src_folder) if f.endswith('.strm')]
            
            for file in files_in_folder:
                # Check if individual file has episode number
                file_episode_match = re.search(r'S(\d+)E(\d+)', file, re.IGNORECASE)
                
                if file_episode_match:
                    # File has specific episode number - use it
                    file_season = int(file_episode_match.group(1))
                    file_episode = int(file_episode_match.group(2))
                    file_season_folder = f"Season {file_season:02d}"
                    
                    # Use clean format without episode titles (media server will handle metadata)
                    file_episode_filename = f"{clean_show_name} S{file_season:02d}E{file_episode:02d}.strm"
                    
                    # Clean filename for filesystem compatibility
                    file_episode_filename = clean_filename(file_episode_filename)
                    
                    file_dest_folder = os.path.join(show_dest_folder, file_season_folder)
                else:
                    # File doesn't have episode number - use folder-based naming
                    file_dest_folder = episode_dest_folder
                    file_episode_filename = clean_filename(episode_filename)
                
                src_file = os.path.join(src_folder, file)
                dest_file = os.path.join(file_dest_folder, file_episode_filename)
                
                # Check if file has been processed before
                if is_file_processed(src_file, tracking_data):
                    logger.debug(f"Skipped TV Show (already processed): {folder_name}/{file}")
                    copied_files += 1
                    continue
                
                if copy_file_if_changed(src_file, dest_file):
                    logger.info(f"Copied TV Show: {folder_name}/{file} -> {file_episode_filename}")
                    mark_file_processed(src_file, tracking_data)
                    copied_files += 1
                else:
                    logger.info(f"Skipped TV Show (unchanged): {folder_name}/{file}")
                    copied_files += 1
    
    return copied_files

def process_movies(movie_folders, unorganized_dir, dest_dirs, tracking_data):
    """Process movie files and copy them to appropriate folders."""
    copied_files = 0
    
    for folder_name in movie_folders:
        src_folder = os.path.join(unorganized_dir, folder_name)
        movie_name = extract_movie_name(folder_name)
        
        if movie_name:
            tmdb_info = search_tmdb_movie(movie_name)
            if tmdb_info:
                movie_folder_name = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}) {{tmdb-{tmdb_info['id']}}}")
                clean_movie_filename = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}).strm")
            else:
                movie_folder_name = clean_filename(movie_name)
                clean_movie_filename = clean_filename(f"{movie_name}.strm")
        else:
            # Fallback: use folder name but clean it up
            clean_folder_name = re.sub(r'\d{4}.*$', '', folder_name).strip()  # Remove year and everything after
            clean_folder_name = re.sub(r'[\.\-_]+', ' ', clean_folder_name).strip()
            movie_folder_name = clean_filename(clean_folder_name)
            clean_movie_filename = clean_filename(f"{clean_folder_name}.strm")
        
        movie_dest_folder = os.path.join(dest_dirs['Movie'], movie_folder_name)
        
        for file in os.listdir(src_folder):
            if file.endswith('.strm'):
                src_file = os.path.join(src_folder, file)
                dest_file = os.path.join(movie_dest_folder, clean_movie_filename)
                
                # Check if file has been processed before
                if is_file_processed(src_file, tracking_data):
                    logger.debug(f"Skipped Movie (already processed): {folder_name}/{file}")
                    copied_files += 1
                    continue
                
                if copy_file_if_changed(src_file, dest_file):
                    logger.info(f"Copied Movie: {folder_name}/{file} -> {clean_movie_filename}")
                    mark_file_processed(src_file, tracking_data)
                    copied_files += 1
                else:
                    logger.info(f"Skipped Movie (unchanged): {folder_name}/{file}")
                    copied_files += 1
    
    return copied_files

# Check and refresh expired .strm files
def refresh_expired_links():
    """Check and refresh expired .strm files (older than 14 days)."""
    for category in ['JAV', 'Shows', 'Movies']:
        category_path = f"/app/media/{category}"
        if not os.path.exists(category_path):
            continue
            
        for root, dirs, files in os.walk(category_path):
            for file in files:
                if file.endswith('.strm'):
                    file_path = os.path.join(root, file)
                    file_age = time.time() - os.path.getmtime(file_path)
                    
                    # 14 days = 1209600 seconds
                    if file_age > 1209600:
                        logger.info(f"Refreshing expired link: {file}")
                        # Here you could trigger re-organization for this file's source
                        # For now, just log it

def process_misc_files(misc_files, dest_dirs):
    """Process individual .strm files from Misc folder based on their category."""
    moved_files = {'JAV': 0, 'Shows': 0, 'Movie': 0}
    
    for misc_file in misc_files:
        file_path = misc_file['file_path']
        category = misc_file['category']
        name = misc_file['name']
        
        try:
            if category == 'JAV':
                # Handle JAV files
                jav_code = extract_jav_code(name)
                if jav_code:
                    jav_folder_name = jav_code
                    jav_filename = f"{jav_code}.strm"
                else:
                    # Fallback to cleaned name
                    clean_name = clean_filename(name)
                    jav_folder_name = clean_name
                    jav_filename = f"{clean_name}.strm"
                
                jav_dest_folder = os.path.join(dest_dirs['JAV'], jav_folder_name)
                dest_file = os.path.join(jav_dest_folder, jav_filename)
                
                if move_file_if_not_exists(file_path, dest_file):
                    logger.info(f"Moved JAV (misc): {misc_file['file']} -> {jav_filename}")
                    moved_files['JAV'] += 1
            
            elif category == 'Shows':
                # Handle TV show files
                show_name = extract_show_name(name)
                if not show_name:
                    show_name = name
                
                tmdb_info = search_tmdb_tv(show_name)
                if tmdb_info:
                    show_folder_name = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}) {{tmdb-{tmdb_info['id']}}}")
                    clean_show_name = clean_filename(tmdb_info['title'])
                else:
                    show_folder_name = clean_filename(show_name)
                    clean_show_name = clean_filename(show_name)
                
                # Try to extract episode info
                season_episode_match = re.search(r'S(\d+)E(\d+)', name, re.IGNORECASE)
                if season_episode_match:
                    season_num = int(season_episode_match.group(1))
                    episode_num = int(season_episode_match.group(2))
                    season_folder = f"Season {season_num:02d}"
                    episode_filename = f"{clean_show_name} S{season_num:02d}E{episode_num:02d}.strm"
                    episode_dest_folder = os.path.join(dest_dirs['Shows'], show_folder_name, season_folder)
                else:
                    # Put in root show folder
                    episode_filename = f"{clean_show_name} E01.strm"
                    episode_dest_folder = os.path.join(dest_dirs['Shows'], show_folder_name)
                
                dest_file = os.path.join(episode_dest_folder, episode_filename)
                
                if move_file_if_not_exists(file_path, dest_file):
                    logger.info(f"Moved Show (misc): {misc_file['file']} -> {episode_filename}")
                    moved_files['Shows'] += 1
            
            elif category == 'Movie':
                # Handle movie files
                movie_name = extract_movie_name(name)
                if not movie_name:
                    movie_name = name
                
                tmdb_info = search_tmdb_movie(movie_name)
                if tmdb_info:
                    movie_folder_name = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}) {{tmdb-{tmdb_info['id']}}}")
                    clean_movie_filename = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}).strm")
                else:
                    movie_folder_name = clean_filename(movie_name)
                    clean_movie_filename = clean_filename(f"{movie_name}.strm")
                
                movie_dest_folder = os.path.join(dest_dirs['Movie'], movie_folder_name)
                dest_file = os.path.join(movie_dest_folder, clean_movie_filename)
                
                if move_file_if_not_exists(file_path, dest_file):
                    logger.info(f"Moved Movie (misc): {misc_file['file']} -> {clean_movie_filename}")
                    moved_files['Movie'] += 1
        
        except Exception as e:
            logger.error(f"Error processing misc file {misc_file['file']}: {e}")
            continue
    
    return moved_files 