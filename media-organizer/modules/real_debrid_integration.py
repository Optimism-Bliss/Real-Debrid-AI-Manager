import os
import json
import logging
import requests
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RealDebridIntegration:
    def __init__(self):
        self.api_key = os.getenv('REAL_DEBRID_API_KEY')
        self.base_url = "https://api.real-debrid.com/rest/1.0"
        self.cache_file = "/app/data/real_debrid_cache.json"
        self.cache = self._load_cache()
        
        if not self.api_key:
            logger.warning("Real-Debrid API key not found. .strm files will not be generated.")
    
    def _load_cache(self) -> Dict:
        """Load Real-Debrid cache."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading Real-Debrid cache: {e}")
        
        return {
            "torrents": {},
            "downloads": {},
            "last_updated": str(datetime.now())
        }
    
    def _save_cache(self):
        """Save Real-Debrid cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving Real-Debrid cache: {e}")
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to Real-Debrid."""
        if not self.api_key:
            return None
        
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data or {})
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Real-Debrid API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making Real-Debrid API request: {e}")
            return None
    
    def get_user_info(self) -> Optional[Dict]:
        """Get user information from Real-Debrid."""
        return self._make_request("user")
    
    def get_torrents(self) -> List[Dict]:
        """Get list of torrents from Real-Debrid."""
        response = self._make_request("torrents")
        if response and isinstance(response, list):
            return response
        return []
    
    def get_downloads(self) -> List[Dict]:
        """Get list of downloads from Real-Debrid."""
        response = self._make_request("downloads")
        if response and isinstance(response, list):
            return response
        return []
    
    def add_torrent(self, magnet_link: str) -> Optional[str]:
        """Add torrent to Real-Debrid."""
        data = {"magnet": magnet_link}
        response = self._make_request("torrents/addMagnet", method="POST", data=data)
        
        if response and "id" in response:
            torrent_id = response["id"]
            logger.info(f"Added torrent to Real-Debrid: {torrent_id}")
            return torrent_id
        
        return None
    
    def select_files(self, torrent_id: str, file_ids: List[str]) -> bool:
        """Select files to download from torrent."""
        data = {"files": ",".join(file_ids)}
        response = self._make_request(f"torrents/selectFiles/{torrent_id}", method="POST", data=data)
        
        if response:
            logger.info(f"Selected files for torrent {torrent_id}")
            return True
        
        return False
    
    def get_torrent_info(self, torrent_id: str) -> Optional[Dict]:
        """Get detailed information about a torrent."""
        return self._make_request(f"torrents/info/{torrent_id}")
    
    def get_download_link(self, link: str) -> Optional[str]:
        """Get direct download link from Real-Debrid."""
        data = {"link": link}
        response = self._make_request("unrestrict/link", method="POST", data=data)
        
        if response and "download" in response:
            return response["download"]
        
        return None
    
    def find_torrent_by_name(self, folder_name: str) -> Optional[Dict]:
        """Find torrent in Real-Debrid by folder name."""
        torrents = self.get_torrents()
        
        for torrent in torrents:
            if self._matches_folder_name(torrent.get("name", ""), folder_name):
                return torrent
        
        return None
    
    def _matches_folder_name(self, torrent_name: str, folder_name: str) -> bool:
        """Check if torrent name matches folder name."""
        # Simple matching - can be improved
        torrent_lower = torrent_name.lower()
        folder_lower = folder_name.lower()
        
        # Remove common extensions and clean up
        torrent_clean = torrent_lower.replace('.mkv', '').replace('.mp4', '').replace('.avi', '')
        folder_clean = folder_lower.replace('.mkv', '').replace('.mp4', '').replace('.avi', '')
        
        # Check if one contains the other
        return torrent_clean in folder_clean or folder_clean in torrent_clean
    
    def generate_strm_url(self, folder_name: str, video_file: str) -> Optional[str]:
        """Generate Real-Debrid URL for .strm file."""
        try:
            # First, try to find existing torrent
            torrent = self.find_torrent_by_name(folder_name)
            
            if torrent:
                torrent_id = torrent["id"]
                torrent_info = self.get_torrent_info(torrent_id)
                
                if torrent_info and torrent_info.get("status") == "downloaded":
                    # Find the specific file
                    for file_info in torrent_info.get("files", []):
                        if self._matches_video_file(file_info.get("path", ""), video_file):
                            # Get download link
                            download_link = self.get_download_link(file_info.get("link", ""))
                            if download_link:
                                logger.info(f"Generated Real-Debrid URL for {video_file}")
                                return download_link
            
            # If not found, try to create new torrent (placeholder)
            logger.warning(f"Could not find existing torrent for {folder_name}")
            return self._create_placeholder_url(folder_name, video_file)
            
        except Exception as e:
            logger.error(f"Error generating Real-Debrid URL for {video_file}: {e}")
            return None
    
    def _matches_video_file(self, torrent_file_path: str, video_file: str) -> bool:
        """Check if torrent file matches video file."""
        torrent_filename = os.path.basename(torrent_file_path)
        video_filename = os.path.basename(video_file)
        
        # Simple filename matching
        return torrent_filename.lower() == video_filename.lower()
    
    def _create_placeholder_url(self, folder_name: str, video_file: str) -> str:
        """Create placeholder URL when Real-Debrid integration is not available."""
        # This is a placeholder - in real implementation, you would:
        # 1. Add torrent to Real-Debrid
        # 2. Wait for completion
        # 3. Get download link
        
        video_filename = os.path.basename(video_file)
        return f"https://sgp1.download.real-debrid.com/d/PLACEHOLDER/{video_filename}"
    
    def monitor_torrent_completion(self, torrent_id: str, callback=None):
        """Monitor torrent completion and call callback when done."""
        def check_completion():
            while True:
                torrent_info = self.get_torrent_info(torrent_id)
                
                if torrent_info and torrent_info.get("status") == "downloaded":
                    logger.info(f"Torrent {torrent_id} completed")
                    if callback:
                        callback(torrent_info)
                    break
                
                time.sleep(30)  # Check every 30 seconds
        
        # Run in background thread
        import threading
        thread = threading.Thread(target=check_completion)
        thread.daemon = True
        thread.start()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cached_torrents": len(self.cache.get("torrents", {})),
            "cached_downloads": len(self.cache.get("downloads", {})),
            "last_updated": self.cache.get("last_updated", "")
        }

# Global instance
real_debrid = RealDebridIntegration() 