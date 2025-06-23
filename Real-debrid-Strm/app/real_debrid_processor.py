#!/usr/bin/env python3
"""
Real Debrid Processor - New workflow with torrent grouping
Combines the best of old Node.js approach with new grouping logic
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote
import subprocess
import os

from .real_debrid_api_client import RealDebridAPIClient
from .strm_manager import STRMManager

logger = logging.getLogger(__name__)

class RealDebridProcessor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.strm_manager = STRMManager()
        
        # File filtering settings
        self.min_video_size_mb = 300  # Minimum video size to avoid ads/junk
        self.allowed_video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.m4v', '.webm', '.flv'}
        self.allowed_subtitle_extensions = {'.srt', '.ass', '.vtt', '.sub', '.idx', '.ssa', '.smi'}
        self.allowed_mime_types = {
            'video/x-matroska',
            'video/mp4', 
            'video/x-msvideo',
            'video/quicktime',
            'video/x-ms-wmv',
            'video/webm',
            'video/x-flv',
            'application/x-subrip',  # SRT
            'text/vtt',              # VTT
            'text/plain',            # Generic subtitle
        }
        
    def sanitize_folder_name(self, name: str) -> str:
        """Sanitize folder name, removing extensions for single files"""
        if not name:
            return "Unknown"
        
        # Remove extension if it's a video or subtitle file (for single file torrents)
        name_path = Path(name)
        if name_path.suffix.lower() in (self.allowed_video_extensions | self.allowed_subtitle_extensions):
            # Remove extension for single files
            name = name_path.stem
            logger.debug(f"📂 Removed extension from folder name: {name_path.name} → {name}")
        
        # Remove problematic characters for folder names
        clean_name = re.sub(r'[<>:"/\\|?*]', '_', name)
        clean_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_name)  # Remove control chars
        clean_name = re.sub(r'\.+$', '', clean_name)  # Remove trailing dots
        clean_name = clean_name.strip()
        
        return clean_name or "Unknown"
    
    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename for STRM files - create clean, readable names
        Removes extension and creates filesystem-safe names
        """
        if not name:
            return "unknown"
        
        # Start with the original name
        clean_name = name
        
        # Decode URL encoding if present
        try:
            # Sometimes filenames are still encoded
            for _ in range(3):
                temp = unquote(clean_name)
                if temp == clean_name:
                    break
                clean_name = temp
        except:
            pass
        
        # Remove file extension first
        clean_name = re.sub(r'\.[^.]+$', '', clean_name)
        
        # Handle common patterns to make cleaner names
        # Remove common prefixes/suffixes
        clean_name = re.sub(r'^(hhd\d+\.com@|hdd\d+\.com@)', '', clean_name)  # Remove site prefixes
        clean_name = re.sub(r'(\.mp4|\.mkv|\.avi)$', '', clean_name, flags=re.IGNORECASE)  # Remove any remaining extensions
        
        # Replace URL encoding artifacts
        clean_name = re.sub(r'%[0-9A-Fa-f]{2}', ' ', clean_name)  # Replace any remaining % encoding
        
        # Clean up brackets and special chars but preserve important ones
        clean_name = re.sub(r'[<>:"/\\|?*]', '_', clean_name)  # Replace truly problematic chars
        clean_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_name)  # Remove control characters
        
        # Normalize spaces and separators
        clean_name = re.sub(r'[._-]+', ' ', clean_name)  # Replace dots, dashes, underscores with spaces
        clean_name = re.sub(r'\s+', ' ', clean_name)  # Collapse multiple spaces
        clean_name = clean_name.strip()
        
        # Remove trailing dots (Windows compatibility)
        clean_name = re.sub(r'\.+$', '', clean_name)
        
        # Intelligent truncation - keep important parts
        if len(clean_name) > 100:  # Shorter limit for readability
            # Try to break at word boundaries
            words = clean_name.split()
            truncated = ""
            for word in words:
                if len(truncated + " " + word) <= 95:
                    truncated += (" " + word) if truncated else word
                else:
                    break
            
            if truncated:
                clean_name = truncated
            else:
                # Fallback: just cut at character limit
                clean_name = clean_name[:95]
        
        # Final cleanup
        clean_name = clean_name.strip()
        
        # Ensure we have something valid
        if not clean_name or len(clean_name) < 3:
            # Try to extract something meaningful from the original
            fallback = re.sub(r'[^\w\s-]', '', name)[:50]
            if fallback.strip():
                clean_name = fallback.strip()
            else:
                clean_name = "media_file"
        
        return clean_name
    
    def extract_filename_from_url(self, url: str) -> str:
        """Extract and decode filename from direct download URL"""
        if not url:
            return "unknown"
        
        try:
            # URLs format: https://sgp1.download.real-debrid.com/d/LINKID/filename.ext
            if "/d/" in url:
                parts = url.split("/")
                if len(parts) > 0:
                    # Get last part (encoded filename)
                    encoded_filename = parts[-1]
                    if encoded_filename and encoded_filename != parts[-2]:  # Not just the link ID
                        # Decode URL encoding multiple times if needed
                        decoded_filename = encoded_filename
                        # Sometimes URLs are double/triple encoded
                        for _ in range(3):
                            try:
                                temp = unquote(decoded_filename)
                                if temp == decoded_filename:
                                    break  # No more decoding needed
                                decoded_filename = temp
                            except:
                                break
                        
                        # Clean up common URL artifacts
                        decoded_filename = decoded_filename.split('?')[0]  # Remove query params
                        decoded_filename = decoded_filename.split('#')[0]  # Remove fragments
                        
                        return decoded_filename
            
            return "unknown"
        except Exception as e:
            logger.debug(f"Failed to extract filename from {url}: {e}")
            return "unknown"
    
    async def process_from_api(self, output_dir: Path, media_dir: Path, skip_existing: bool = False, existing_urls: Optional[set] = None, cycle_mode: bool = False) -> Dict:
        """
        Process via Real Debrid API with optional skip existing files logic
        
        Args:
            output_dir: Directory to save API data
            media_dir: Directory to create STRM files  
            skip_existing: Whether to skip URLs that already have STRM files
            existing_urls: Set of URLs to skip (used with skip_existing)
            cycle_mode: Whether running in cycle mode (affects logging)
        """
        if cycle_mode:
            logger.info("🔄 Running API processing in cycle mode")
        else:
            logger.info("📡 Running API processing in standalone mode")
        
        if not self.api_key:
            return {"success": False, "error": "No API key provided"}
        
        try:
            # Step 1: Load or fetch API data
            torrents_file = output_dir / "realdebrid_torrents.json"
            unrestricted_file = output_dir / "realdebrid_unrestricted.json"
            
            # Use existing data if available and not in cycle mode
            if not cycle_mode and torrents_file.exists() and unrestricted_file.exists():
                logger.info("📁 Using existing API data files")
                with open(torrents_file, 'r', encoding='utf-8') as f:
                    torrents = json.load(f)
                with open(unrestricted_file, 'r', encoding='utf-8') as f:
                    unrestricted_data = json.load(f)
                
                result = {"success": True, "source": "existing_files"}
            else:
                # Fetch fresh data from API
                logger.info("📡 Fetching fresh data from Real Debrid API")
                client = RealDebridAPIClient(self.api_key)
                result = await client.process_torrents_with_grouping(output_dir)
                
                if not result.get("success"):
                    return result
                
                # Load the fresh data
                with open(torrents_file, 'r', encoding='utf-8') as f:
                    torrents = json.load(f)
                with open(unrestricted_file, 'r', encoding='utf-8') as f:
                    unrestricted_data = json.load(f)
            
            # Step 2: Create torrent grouping with skip logic
            logger.info("📂 Creating torrent grouping...")
            torrent_groups = self._create_torrent_groups_with_skip(
                torrents, 
                unrestricted_data, 
                skip_existing=skip_existing,
                existing_urls=existing_urls or set()
            )
            
            # Step 3: Create STRM files
            logger.info("📄 Creating STRM files...")
            strm_results = self._create_grouped_strm_files(torrent_groups, media_dir)
            
            # Step 4: Generate summary
            summary = {
                "success": True,
                "source": result.get("source", "api"),
                "cycle_mode": cycle_mode,
                "torrents_processed": len(torrent_groups),
                "total_files": sum(len(group['files']) for group in torrent_groups.values()),
                "strm_files_created": strm_results['created'],
                "strm_files_skipped": strm_results['skipped'],
                "folders_created": len([g for g in torrent_groups.values() if g['files']]),
                "api_data": result,
                "skip_stats": {
                    "skip_existing_enabled": skip_existing,
                    "existing_urls_provided": len(existing_urls) if existing_urls else 0
                }
            }
            return summary
        except Exception as e:
            logger.error(f"❌ Error in API processing: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _create_torrent_groups_with_skip(self, torrents: List[Dict], unrestricted_data: List[Dict], skip_existing: bool = False, existing_urls: Optional[set] = None) -> Dict:
        """Create torrent groups, but skip files that already have STRM files"""
        if existing_urls is None:
            existing_urls = set()
            
        logger.info("📂 Creating torrent groups with skip logic...")
        
        # Create a map of torrents by their ID for quick lookup, safely skipping those without an ID
        torrent_map = {}
        for t in torrents:
            if 'id' in t and t['id']:
                torrent_map[t['id']] = t
            else:
                logger.warning(f"Skipping torrent due to missing 'id': {t.get('filename', 'Unknown')}")

        torrent_groups = {}
        processed_links = set()
        unrestricted_map = {item['id']: item for item in unrestricted_data if 'id' in item and item['id']}

        for item in unrestricted_data:
            link = item.get('link')
            torrent_id = item.get('torrent_id')
            
            # Ensure torrent_id exists and is in our map
            if not torrent_id or torrent_id not in torrent_map:
                continue

            # Skip if URL already exists
            if skip_existing and existing_urls and link in existing_urls:
                continue

            if link and link not in processed_links:
                original_filename = item.get('filename') or self.extract_filename_from_url(item.get('download', ''))
                filesize = item.get('filesize', 0)
                
                should_proc = self.should_process_file(original_filename, filesize)
                if not should_proc['process']:
                    logger.debug(f"Skipping file (filter): {original_filename} ({should_proc['reason']})")
                    continue
                
                torrent_info = torrent_map.get(torrent_id, {})
                group_name = self.sanitize_folder_name(torrent_info.get('filename', original_filename))
                
                if group_name not in torrent_groups:
                    torrent_groups[group_name] = {
                        'folder_name': group_name,
                        'files': [],
                        'torrent_info': torrent_info
                    }
                
                sanitized_name = self.sanitize_filename(original_filename)
                
                torrent_groups[group_name]['files'].append({
                    'url': item.get('download'),
                    'filename': sanitized_name,
                    'original_filename': original_filename,
                    'filesize': filesize
                })
                processed_links.add(link)

        logger.info(f"📁 Created {len(torrent_groups)} groups")
        return torrent_groups
        
    def _create_grouped_strm_files(self, torrent_groups: Dict, media_dir: Path) -> Dict:
        """
        Create STRM files from torrent groups into a structured folder layout
        """
        logger.info(f"📄 Creating STRM files for {len(torrent_groups)} groups...")
        created_count = 0
        skipped_count = 0
        
        unorganized_dir = media_dir / "unorganized"
        unorganized_dir.mkdir(exist_ok=True)
        
        for group_name, group_data in torrent_groups.items():
            files = group_data.get('files', [])
            if not files:
                continue
            
            # Sanitize the group name to create a valid folder name
            folder_name = self.sanitize_folder_name(group_name)
            
            logger.info(f"📂 Processing group: {folder_name} ({len(files)} files)")
            
            for file_data in files:
                url = file_data.get('url')
                sanitized_filename = file_data.get('filename', 'unknown')
                
                if not url:
                    logger.warning(f"Skipping file with no URL: {sanitized_filename}")
                    skipped_count += 1
                    continue
                
                # Use the dedicated method to create a STRM file in a specific folder
                try:
                    # The media_path is handled by the strm_manager, so we just provide the relative folder name
                    self.strm_manager.create_strm_file_in_folder(url, sanitized_filename, folder_name)
                    created_count += 1
                except Exception as e:
                    logger.error(f"Failed to create STRM file for {sanitized_filename} in {folder_name}: {e}")
                    skipped_count += 1
        
        return {"created": created_count, "skipped": skipped_count}
        
    def process_from_files(self, data_dir: Path, media_dir: Path) -> Dict:
        """
        Main processing function - loads from local JSON files
        This is useful for debugging and reprocessing without hitting the API
        
        Args:
            data_dir: Path to directory with JSON files (realdebrid_torrents.json, etc.)
            media_dir: Root directory for media (e.g., /app/media)
        
        Returns:
            Dictionary with processing results
        """
        logger.info(f"🔄 Processing from local files in: {data_dir}")
        
        # Load torrents data
        torrents_file = data_dir / "realdebrid_torrents.json"
        if not torrents_file.exists():
            return {"success": False, "error": "realdebrid_torrents.json not found"}
        with open(torrents_file, 'r', encoding='utf-8') as f:
            torrents = json.load(f)
        
        # Load unrestricted links data
        unrestricted_file = data_dir / "realdebrid_unrestricted.json"
        if not unrestricted_file.exists():
            return {"success": False, "error": "realdebrid_unrestricted.json not found"}
        with open(unrestricted_file, 'r', encoding='utf-8') as f:
            unrestricted_data = json.load(f)
        
        # Create torrent groups
        logger.info("📂 Creating torrent groups...")
        torrent_groups = self._create_torrent_groups(torrents, unrestricted_data)
        
        # Create STRM files
        logger.info("📄 Creating STRM files...")
        strm_results = self._create_strm_files_from_groups(torrent_groups, media_dir)
        
        # Generate summary
        summary = {
            "success": True,
            "torrents_processed": len(torrent_groups),
            "total_files": sum(len(group['files']) for group in torrent_groups.values()),
            "strm_files_created": strm_results['created'],
            "strm_files_skipped": strm_results['skipped'],
            "folders_created": len(torrent_groups)
        }
        
        logger.info("✅ Processing from files complete!")
        return summary
        
    def _create_strm_files_from_groups(self, torrent_groups: Dict, media_dir: Path) -> Dict:
        """
        Creates STRM files based on the grouped torrents.
        Each group becomes a folder in /unorganized.
        """
        unorganized_dir = media_dir / "unorganized"
        unorganized_dir.mkdir(exist_ok=True)
        
        created_count = 0
        skipped_count = 0
        
        for group_id, group_info in torrent_groups.items():
            folder_name = self.sanitize_folder_name(group_info['name'])
            
            for file_info in group_info['files']:
                url = file_info.get('url')
                filename = file_info.get('sanitized_name', 'unknown_file')
                
                if url:
                    try:
                        self.strm_manager.create_strm_file_in_folder(url, filename, folder_name)
                        created_count += 1
                    except Exception as e:
                        logger.error(f"Error creating STRM file for {filename} in {folder_name}: {e}")
                        skipped_count += 1
                else:
                    skipped_count += 1
        
        logger.info(f"📄 Created {created_count} STRM files, skipped {skipped_count}")
        return {"created": created_count, "skipped": skipped_count}

    def get_summary(self, media_dir: Path) -> Dict:
        """
        Provide a summary of the current media structure
        """
        unorganized_dir = media_dir / "unorganized"
        
        if not unorganized_dir.exists():
            return {"error": "Unorganized directory not found"}
        
        summary = {
            "unorganized_folders": 0,
            "unorganized_strm_files": 0,
            "top_level_items": []
        }
        
        for item in unorganized_dir.iterdir():
            summary['top_level_items'].append(item.name)
            if item.is_dir():
                summary['unorganized_folders'] += 1
                summary['unorganized_strm_files'] += len(list(item.glob('*.strm')))
        
        return summary
        
    def should_process_file(self, filename: str, filesize: int = 0, mime_type: str = "") -> Dict:
        """
        Advanced filter to decide if a file should be processed
        """
        if not filename:
            return {"process": False, "reason": "No filename"}

        file_ext = Path(filename).suffix.lower()
        
        # Check if it's a video file
        is_video = file_ext in self.allowed_video_extensions or (mime_type and 'video' in mime_type)
        
        # Check if it's a subtitle file
        is_subtitle = file_ext in self.allowed_subtitle_extensions or (mime_type and 'sub' in mime_type)
        
        if not is_video and not is_subtitle:
            return {"process": False, "reason": f"Unsupported extension: {file_ext}"}
        
        # Check size for video files
        if is_video and self.min_video_size_mb > 0:
            if filesize < (self.min_video_size_mb * 1024 * 1024):
                return {"process": False, "reason": f"Video file too small: {filesize/1024/1024:.2f}MB"}
        
        # Categorize the file
        category = "Video" if is_video else "Subtitle"
        
        return {"process": True, "reason": "File meets criteria", "category": category}

    def configure_filtering(self, min_video_size_mb: Optional[int] = None, additional_video_exts: Optional[List[str]] = None, additional_subtitle_exts: Optional[List[str]] = None):
        """
        Configure file filtering settings at runtime
        """
        if min_video_size_mb is not None:
            self.min_video_size_mb = min_video_size_mb
            logger.info(f"🔧 Set minimum video size to {min_video_size_mb} MB")
            
        if additional_video_exts:
            for ext in additional_video_exts:
                if ext and not ext.startswith('.'):
                    ext = '.' + ext
                self.allowed_video_extensions.add(ext.lower())
            logger.info(f"🔧 Added video extensions: {additional_video_exts}")

        if additional_subtitle_exts:
            for ext in additional_subtitle_exts:
                if ext and not ext.startswith('.'):
                    ext = '.' + ext
                self.allowed_subtitle_extensions.add(ext.lower())
            logger.info(f"🔧 Added subtitle extensions: {additional_subtitle_exts}")
        
        logger.info(f"🔧 Filtering configured: Min Size={self.min_video_size_mb}MB, "
                    f"Video Exts={len(self.allowed_video_extensions)}, "
                    f"Subtitle Exts={len(self.allowed_subtitle_extensions)}")
        
    def get_filtering_config(self) -> Dict:
        """Get current filtering configuration"""
        return {
            "min_video_size_mb": self.min_video_size_mb,
            "allowed_video_extensions": list(self.allowed_video_extensions),
            "allowed_subtitle_extensions": list(self.allowed_subtitle_extensions)
        }
        
    def _create_torrent_groups(self, torrents: List[Dict], unrestricted_data: List[Dict]) -> Dict:
        """Create torrent groups from API data"""
        logger.info("📂 Creating torrent groups...")
        
        # Create a map of torrents by their ID for quick lookup, safely skipping those without an ID
        torrent_map = {}
        for t in torrents:
            if 'id' in t and t['id']:
                torrent_map[t['id']] = t
            else:
                logger.warning(f"Skipping torrent due to missing 'id': {t.get('filename', 'Unknown')}")

        torrent_groups = {}
        processed_links = set()
        unrestricted_map = {item['id']: item for item in unrestricted_data if 'id' in item and item['id']}

        for item in unrestricted_data:
            link = item.get('link')
            torrent_id = item.get('torrent_id')
            
            # Ensure torrent_id exists and is in our map
            if not torrent_id or torrent_id not in torrent_map:
                continue

            if link and link not in processed_links:
                original_filename = item.get('filename') or self.extract_filename_from_url(item.get('download', ''))
                filesize = item.get('filesize', 0)
                
                should_proc = self.should_process_file(original_filename, filesize)
                if not should_proc['process']:
                    logger.debug(f"Skipping file (filter): {original_filename} ({should_proc['reason']})")
                    continue
                
                torrent_info = torrent_map.get(torrent_id, {})
                group_name = self.sanitize_folder_name(torrent_info.get('filename', original_filename))
                
                if group_name not in torrent_groups:
                    torrent_groups[group_name] = {
                        'folder_name': group_name,
                        'files': [],
                        'torrent_info': torrent_info
                    }
                
                sanitized_name = self.sanitize_filename(original_filename)
                
                torrent_groups[group_name]['files'].append({
                    'url': item.get('download'),
                    'filename': sanitized_name,
                    'original_filename': original_filename,
                    'filesize': filesize
                })
                processed_links.add(link)

        logger.info(f"📁 Created {len(torrent_groups)} groups")
        return torrent_groups 