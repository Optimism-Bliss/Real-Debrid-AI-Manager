import os
import re
import logging
from .smart_cache import smart_cache
from .tmdb_api import search_tmdb_movie_by_id, search_tmdb_show_by_id
from .processors import clean_filename
from .config import DEST_DIRS

logger = logging.getLogger(__name__)

def apply_metadata_correction(original_folder_name: str, correct_tmdb_id: str, reason: str = ""):
    """
    Applies a metadata correction for a misidentified movie or show.
    1. Finds the old, incorrectly named destination folder.
    2. Fetches correct metadata from TMDB using the new ID.
    3. Renames the folder and the .strm file(s) inside.
    4. Updates the cache to prevent this from happening again.
    """
    logger.info(f"Applying metadata correction for '{original_folder_name}' with new TMDB ID: {correct_tmdb_id}")

    # Step 1: Find the old, incorrectly named destination folder from cache
    cached_info = smart_cache.get_cached_item(original_folder_name)
    if not cached_info or not cached_info.get("dest_path"):
        msg = f"Cannot apply correction: No existing destination path found in cache for '{original_folder_name}'. Please process the file first."
        logger.warning(msg)
        return {'success': False, 'message': msg}

    old_dest_path = cached_info["dest_path"]
    classification = cached_info["classification"]

    if classification not in ["Movie", "Shows"]:
        msg = f"Metadata correction only applicable for Movies/Shows, but classification was '{classification}'."
        logger.warning(msg)
        return {'success': False, 'message': msg}

    if not os.path.exists(old_dest_path):
        msg = f"Cannot apply correction: The destination folder '{old_dest_path}' does not exist anymore."
        logger.warning(msg)
        # Still, we should save the correction for future processing
        smart_cache.add_manual_correction(original_folder_name, classification, classification, reason, correct_tmdb_id)
        return {'success': True, 'message': f"Saved correction for future runs, but couldn't find folder to rename."}


    # Step 2: Fetch correct metadata from TMDB
    tmdb_info = None
    if classification == "Movie":
        tmdb_info = search_tmdb_movie_by_id(correct_tmdb_id)
    elif classification == "Shows":
        tmdb_info = search_tmdb_show_by_id(correct_tmdb_id)

    if not tmdb_info:
        msg = f"Failed to fetch metadata from TMDB for ID: {correct_tmdb_id}"
        logger.error(msg)
        return {'success': False, 'message': msg}

    # Step 3: Rename the folder and the .strm file(s)
    try:
        # Create new folder name
        new_folder_name = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}) {{tmdb-{tmdb_info['id']}}}")
        parent_dir = os.path.dirname(old_dest_path)
        new_dest_path = os.path.join(parent_dir, new_folder_name)

        # Rename folder
        os.rename(old_dest_path, new_dest_path)
        logger.info(f"Renamed folder: '{old_dest_path}' -> '{new_dest_path}'")

        # Rename .strm files inside
        for filename in os.listdir(new_dest_path):
            if filename.endswith(".strm"):
                clean_strm_name = ""
                if classification == "Movie":
                     clean_strm_name = clean_filename(f"{tmdb_info['title']} ({tmdb_info['year']}).strm")
                elif classification == "Shows":
                    # Attempt to preserve season/episode info if present in old name
                    match = re.search(r'(S\d{2}E\d{2})', filename)
                    se_part = match.group(1) if match else "S01E01" # fallback
                    clean_strm_name = clean_filename(f"{tmdb_info['title']} {se_part}.strm")
                
                old_strm_path = os.path.join(new_dest_path, filename)
                new_strm_path = os.path.join(new_dest_path, clean_strm_name)
                os.rename(old_strm_path, new_strm_path)
                logger.info(f"Renamed .strm file: '{filename}' -> '{clean_strm_name}'")

    except Exception as e:
        msg = f"Error renaming files: {e}"
        logger.error(msg, exc_info=True)
        # Attempt to rollback rename if it happened
        if 'new_dest_path' in locals() and os.path.exists(new_dest_path):
            os.rename(new_dest_path, old_dest_path)
        return {'success': False, 'message': msg}

    # Step 4: Update the cache and save the correction rule
    smart_cache.add_manual_correction(original_folder_name, classification, classification, reason, correct_tmdb_id)
    smart_cache.update_cached_item(original_folder_name, {"dest_path": new_dest_path})
    
    logger.info(f"Successfully applied correction for '{original_folder_name}'")
    return {'success': True, 'message': f"Successfully corrected and renamed to '{new_folder_name}'."} 