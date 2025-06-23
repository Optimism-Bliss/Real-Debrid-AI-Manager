#!/usr/bin/env python3
"""
Cleanup script to remove processed files from unorganized directory.
This script should be run periodically to clean up files that have been successfully processed.
"""

import os
import json
import logging
from modules.utils import load_tracking, get_file_tracking_key, TRACK_FILE
from modules.config import UNORGANIZED_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cleanup_processed_files():
    """Remove files from unorganized directory that have been successfully processed."""
    
    # Load tracking data
    tracking_data = load_tracking()
    if not tracking_data:
        logger.warning("No tracking data found. Nothing to clean up.")
        return
    
    logger.info(f"Loaded tracking data for {len(tracking_data)} files")
    
    # Find and remove processed files
    removed_count = 0
    removed_folders = set()
    
    for root, dirs, files in os.walk(UNORGANIZED_DIR):
        for file in files:
            if file.endswith('.strm'):
                file_path = os.path.join(root, file)
                
                # Check if this file has been processed
                tracking_key = get_file_tracking_key(file_path)
                if tracking_key in tracking_data:
                    try:
                        os.remove(file_path)
                        logger.debug(f"Removed processed file: {file_path}")
                        removed_count += 1
                        
                        # Mark folder for potential removal
                        removed_folders.add(root)
                    except OSError as e:
                        logger.error(f"Error removing file {file_path}: {e}")
    
    # Remove empty folders
    folders_removed = 0
    for folder in sorted(removed_folders, key=len, reverse=True):  # Remove deepest folders first
        try:
            if os.path.exists(folder) and not os.listdir(folder):  # Check if folder is empty
                os.rmdir(folder)
                logger.debug(f"Removed empty folder: {folder}")
                folders_removed += 1
        except OSError as e:
            logger.error(f"Error removing folder {folder}: {e}")
    
    logger.info(f"Cleanup completed:")
    logger.info(f"  Files removed: {removed_count}")
    logger.info(f"  Empty folders removed: {folders_removed}")
    
    # Clean up tracking data for removed files
    if removed_count > 0:
        cleanup_tracking_data(tracking_data)
        logger.info("Tracking data cleaned up")

def cleanup_tracking_data(tracking_data):
    """Remove tracking entries for files that no longer exist."""
    original_count = len(tracking_data)
    
    # Remove entries for files that don't exist
    keys_to_remove = []
    for tracking_key, data in tracking_data.items():
        file_path = data.get('file_path', tracking_key.split(':')[0])
        if not os.path.exists(file_path):
            keys_to_remove.append(tracking_key)
    
    for key in keys_to_remove:
        del tracking_data[key]
    
    # Save cleaned tracking data
    try:
        with open(TRACK_FILE, 'w') as f:
            json.dump(tracking_data, f, indent=2)
        logger.info(f"Tracking data cleaned: {original_count} -> {len(tracking_data)} entries")
    except Exception as e:
        logger.error(f"Error saving tracking data: {e}")

if __name__ == "__main__":
    logger.info("Starting cleanup of processed files...")
    cleanup_processed_files()
    logger.info("Cleanup completed!") 