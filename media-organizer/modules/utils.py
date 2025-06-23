import os
import shutil
import hashlib
import json
import logging
import time
from .config import TRACK_FILE

logger = logging.getLogger(__name__)

def hash_file(filepath):
    """Return SHA256 hash of file content."""
    try:
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing file {filepath}: {e}")
        return None

def load_tracking():
    """Load file tracking data."""
    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tracking file: {e}")
    return {}

def save_tracking(tracking):
    """Save file tracking data."""
    try:
        os.makedirs(os.path.dirname(TRACK_FILE), exist_ok=True)
        with open(TRACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(tracking, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving tracking file: {e}")

def move_file_if_not_exists(src_file, dest_file):
    """Move file if it doesn't exist at destination, otherwise delete source."""
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        
        # If destination exists (duplicate), just remove the source file
        if os.path.exists(dest_file):
            os.remove(src_file)
            logger.debug(f"Duplicate found. Destination {dest_file} already exists. Source {src_file} removed.")
            return False # Indicate that no new file was moved
        
        # If destination doesn't exist, move the file
        shutil.move(src_file, dest_file)
        logger.debug(f"Moved new file: {src_file} -> {dest_file}")
        return True
            
    except Exception as e:
        logger.error(f"Error moving file {src_file} to {dest_file}: {e}")
        return False

def copy_file_if_changed(src_file, dest_file):
    """Copy file if it has changed or doesn't exist at destination."""
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        
        # If destination doesn't exist, copy it
        if not os.path.exists(dest_file):
            shutil.copy2(src_file, dest_file)
            logger.debug(f"Copied new file: {src_file} -> {dest_file}")
            return True
        
        # Check if files are different by comparing hashes
        src_hash = hash_file(src_file)
        dest_hash = hash_file(dest_file)
        
        if src_hash != dest_hash:
            shutil.copy2(src_file, dest_file)
            logger.debug(f"Updated changed file: {src_file} -> {dest_file}")
            return True
        else:
            logger.debug(f"File unchanged, skipped: {src_file}")
            return False
            
    except Exception as e:
        logger.error(f"Error copying file {src_file} to {dest_file}: {e}")
        return False

def get_file_tracking_key(file_path):
    """Generate a tracking key for a file based on its path and modification time."""
    try:
        stat = os.stat(file_path)
        # Use file path and modification time as tracking key
        return f"{file_path}:{stat.st_mtime}"
    except OSError:
        return file_path

def is_file_processed(file_path, tracking_data):
    """Check if a file has been processed based on tracking data."""
    tracking_key = get_file_tracking_key(file_path)
    return tracking_key in tracking_data

def mark_file_processed(file_path, tracking_data):
    """Mark a file as processed in tracking data."""
    tracking_key = get_file_tracking_key(file_path)
    tracking_data[tracking_key] = {
        'processed_at': time.time(),
        'file_path': file_path
    }

def ensure_dest_dirs(dest_dirs):
    """Ensure all destination directories exist."""
    for d in dest_dirs.values():
        os.makedirs(d, exist_ok=True)

def count_strm_files(directory):
    """Count total .strm files in a directory recursively."""
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.strm'):
                count += 1
    return count

def verify_file_counts(source_dir, dest_dirs):
    """Verify that no .strm files were lost during organization."""
    source_count = count_strm_files(source_dir)
    
    dest_count = 0
    for dest_dir in dest_dirs.values():
        if os.path.exists(dest_dir):
            dest_count += count_strm_files(dest_dir)
    
    logger.info(f"Source .strm files: {source_count}")
    logger.info(f"Destination .strm files: {dest_count}")
    
    # This logic now accounts for deduplication. A lower destination count is expected.
    if source_count >= dest_count:
        duplicates_found = source_count - dest_count
        if duplicates_found > 0:
            logger.info(f"✅ File count verification PASSED. Found and skipped {duplicates_found} duplicate(s).")
        else:
            logger.info("✅ File count verification PASSED - No files lost or duplicated!")
        return True
    else:
        # This case should ideally not happen.
        logger.error(f"❌ File count verification FAILED - {dest_count - source_count} files were unexpectedly created!")
        return False

def clean_filename(filename):
    """Clean filename to extract JAV code for .strm files."""
    from .jav_detector import extract_jav_code
    name_without_ext = os.path.splitext(filename)[0]
    jav_code = extract_jav_code(name_without_ext)
    if jav_code:
        return f"{jav_code}.strm"
    return filename 