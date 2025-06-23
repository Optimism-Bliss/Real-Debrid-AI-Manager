#!/usr/bin/env python3
"""
Media Organizer and Monitor
Consolidated script for all media organization tasks.
- Runs a full scan on startup.
- Uses watchdog for real-time monitoring of new folders.
- Periodically scans as a fallback mechanism.
- Integrates logic from organize_media.py directly.
"""

import os
import time
import logging
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirCreatedEvent

# --- Module Imports from original organize_media.py ---
from modules.config import UNORGANIZED_DIR, DEST_DIRS, TRACK_FILE
from modules.utils import (
    load_tracking, save_tracking, ensure_dest_dirs,
    count_strm_files, verify_file_counts
)
from modules.classifier import classify_folder
from modules.api_extractors import extract_show_name
from modules.processors import (
    process_jav_files, process_tv_shows,
    process_movies
)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Global Variables ---
ORGANIZATION_LOCK = threading.Lock()
LAST_ORGANIZED_TIME = 0

def organize_media(reason="Scheduled Scan"):
    """
    Main function to organize media files.
    This logic is adapted from the original organize_media.py.
    """
    global LAST_ORGANIZED_TIME
    if not ORGANIZATION_LOCK.acquire(blocking=False):
        logger.info("Organization is already in progress. Skipping run.")
        return

    try:
        logger.info(f"🚀 Starting media organization ({reason})...")
        ensure_dest_dirs(DEST_DIRS)
        tracking_data = load_tracking()

        if not os.path.exists(UNORGANIZED_DIR):
            logger.error(f"Unorganized directory not found: {UNORGANIZED_DIR}")
            return

        categorized_folders = {'JAV': [], 'Shows': {}, 'Movie': []}

        for entry in os.scandir(UNORGANIZED_DIR):
            if entry.is_dir():
                folder_name = entry.name
                category = classify_folder(folder_name)

                if category == 'SKIP':
                    logger.warning(f"Skipping spam/ad folder: {folder_name}")
                    continue
                elif category == 'JAV':
                    categorized_folders['JAV'].append(folder_name)
                elif category == 'Shows':
                    show_name = extract_show_name(folder_name)
                    if show_name:
                        if show_name not in categorized_folders['Shows']:
                            categorized_folders['Shows'][show_name] = []
                        categorized_folders['Shows'][show_name].append(folder_name)
                else:  # Movie or other categories handled by process_movies
                    categorized_folders['Movie'].append(folder_name)

        logger.info(f"Discovered: {len(categorized_folders['JAV'])} JAV, "
                    f"{len(categorized_folders['Shows'])} shows, "
                    f"{len(categorized_folders['Movie'])} movies.")

        # Process each category
        jav_copied = process_jav_files(categorized_folders['JAV'], UNORGANIZED_DIR, DEST_DIRS, tracking_data)
        shows_copied = process_tv_shows(categorized_folders['Shows'], UNORGANIZED_DIR, DEST_DIRS, tracking_data)
        movies_copied = process_movies(categorized_folders['Movie'], UNORGANIZED_DIR, DEST_DIRS, tracking_data)

        total_copied = jav_copied + shows_copied + movies_copied
        if total_copied > 0:
            logger.info(f"✅ Processing complete. Copied {total_copied} new files.")
            save_tracking(tracking_data)
        else:
            logger.info("✅ No new files to process.")

        LAST_ORGANIZED_TIME = time.time()

    except Exception as e:
        logger.exception(f"An unexpected error occurred during organization: {e}")
    finally:
        ORGANIZATION_LOCK.release()
        logger.info("🏁 Media organization run finished.")


class NewFolderHandler(FileSystemEventHandler):
    """Triggers organization when a new directory is created."""
    def __init__(self, debounce_seconds=60):
        self.debounce_seconds = debounce_seconds
        self.last_triggered_time = 0

    def on_created(self, event):
        if isinstance(event, DirCreatedEvent):
            current_time = time.time()
            if current_time - self.last_triggered_time > self.debounce_seconds:
                logger.info(f"👀 New folder detected: {event.src_path}. Triggering organization.")
                # Run in a new thread to avoid blocking the watchdog observer
                threading.Thread(target=organize_media, args=("New Folder",)).start()
                self.last_triggered_time = current_time
            else:
                logger.info(f"Skipping immediate trigger for {event.src_path} due to debounce.")

def periodic_scanner(interval_minutes):
    """Runs the organization task at a set interval."""
    while True:
        wait_seconds = interval_minutes * 60
        logger.info(f"🗓️ Next scheduled scan in {interval_minutes} minutes.")
        time.sleep(wait_seconds)
        organize_media("Scheduled Scan")

def main():
    """Main entry point for the media organizer and monitor."""
    logger.info("Starting Media Organizer and Monitor Service")
    
    # Get configuration from environment variables
    monitor_interval_minutes = int(os.getenv('MONITOR_INTERVAL_MINUTES', '30'))
    debounce_seconds = int(os.getenv('ORGANIZE_DELAY_SECONDS', '60'))

    # Run an initial scan on startup
    logger.info("Running initial organization scan on startup...")
    initial_scan_thread = threading.Thread(target=organize_media, args=("Startup",))
    initial_scan_thread.start()

    # Start the watchdog observer for real-time monitoring
    event_handler = NewFolderHandler(debounce_seconds=debounce_seconds)
    observer = Observer()
    observer.schedule(event_handler, UNORGANIZED_DIR, recursive=False)
    observer.start()
    logger.info(f"👀 Real-time monitoring started for {UNORGANIZED_DIR}")

    # Start the periodic scanner as a fallback
    scanner_thread = threading.Thread(target=periodic_scanner, args=(monitor_interval_minutes,))
    scanner_thread.daemon = True  # Allows main thread to exit even if this one is running
    scanner_thread.start()
    logger.info(f"🕒 Periodic scanner configured to run every {monitor_interval_minutes} minutes.")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down monitor...")
        observer.stop()
        observer.join()
        logger.info("✅ Monitor shut down gracefully.")

if __name__ == "__main__":
    main() 