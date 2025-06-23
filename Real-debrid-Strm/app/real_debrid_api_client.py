#!/usr/bin/env python3
"""
Real Debrid API Client with rate limiting and batch processing
Inspired by the Node.js version but with torrent grouping
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class RealDebridAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.real-debrid.com/rest/1.0"
        
        # General API rate limiting (for unrestrict, etc.)
        self.general_rate_limit_per_minute = 200
        self.general_request_times = []

        # Stricter rate limiting for /torrents endpoint
        self.torrents_rate_limit_per_minute = 70  # Conservative limit
        self.torrents_request_times = []

        self.concurrency_limit = 2  # Reduced concurrency
        
        # Retry configuration from environment
        self.retry_503_attempts = int(os.getenv('RETRY_503_ATTEMPTS', '2'))
        self.retry_429_attempts = int(os.getenv('RETRY_429_ATTEMPTS', '3'))
        
        logger.info(f"🔧 API Client Configuration:")
        logger.info(f"   ⏱️  General Rate Limit: {self.general_rate_limit_per_minute} req/min")
        logger.info(f"   📂 Torrents Rate Limit: {self.torrents_rate_limit_per_minute} req/min")
        logger.info(f"   🔗 Concurrency: {self.concurrency_limit} simultaneous")
        logger.info(f"   🔄 503 retries: {self.retry_503_attempts}")
        logger.info(f"   ⏱️  429 retries: {self.retry_429_attempts}")
        
        # Request tracking
        self.request_times = []
        
    async def fetch_torrents(self) -> List[Dict]:
        """Fetch ALL torrents from Real Debrid API with pagination"""
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        all_torrents = []
        page = 1
        limit = 100  # Max per page
        
        logger.info("🔄 Fetching torrents with pagination...")
        
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    url = f"{self.base_url}/torrents?page={page}&limit={limit}"
                    logger.debug(f"Fetching page {page}...")
                    
                    await self._enforce_rate_limit(endpoint_type='torrents')
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if not data:  # Empty page = end of data
                                logger.info(f"📄 No more torrents on page {page}, stopping")
                                break
                            
                            all_torrents.extend(data)
                            logger.info(f"📄 Page {page}: {len(data)} torrents (total: {len(all_torrents)})")
                            
                            # If we got less than limit, we're done
                            if len(data) < limit:
                                logger.info(f"✅ Last page reached (got {len(data)} < {limit})")
                                break
                            
                            page += 1
                            
                            # Safety check to prevent infinite loop
                            if page > 1000:  # Max 100,000 torrents
                                logger.warning("⚠️  Safety limit reached (1000 pages), stopping")
                                break
                                
                        elif response.status == 404:
                            logger.info(f"📄 Page {page} not found, stopping pagination")
                            break
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ API error on page {page}: {response.status} - {error_text}")
                            break
                
                logger.info(f"🎉 Fetched {len(all_torrents)} total torrents from {page-1} pages")
                return all_torrents
                
        except Exception as e:
            logger.error(f"❌ Error fetching torrents: {e}")
            return all_torrents  # Return what we have so far
    
    async def unrestrict_link(self, session: aiohttp.ClientSession, link: str) -> Dict:
        """Unrestrict a single link with specific retry logic for different error types"""
        
        url = f"{self.base_url}/unrestrict/link"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"link": link}
        
        # Different retry strategies for different errors
        rate_limit_retries = self.retry_429_attempts
        server_error_retries = self.retry_503_attempts
        base_delay = 2.0
        
        rate_limit_attempts = 0
        server_error_attempts = 0
        
        while True:
            # Rate limiting for general endpoints
            await self._enforce_rate_limit(endpoint_type='general')
            
            try:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"✅ Successfully unrestricted: {link}")
                        return {"link": link, "result": result, "status": "success"}
                    
                    elif response.status == 429:
                        # Rate limit hit - exponential backoff
                        rate_limit_attempts += 1
                        if rate_limit_attempts <= rate_limit_retries:
                            wait_time = base_delay * (2 ** (rate_limit_attempts - 1))  # 2s, 4s, 8s
                            logger.warning(f"⏱️  Rate limit hit for {link}, waiting {wait_time}s (attempt {rate_limit_attempts}/{rate_limit_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ Rate limit exceeded after {rate_limit_retries} retries: {link}")
                            return {"link": link, "error": "rate_limit_exceeded", "status": "failed_rate_limit"}
                    
                    elif response.status == 503:
                        # Server unavailable - retry with shorter delays
                        server_error_attempts += 1
                        if server_error_attempts <= server_error_retries:
                            wait_time = 10.0  # 10 second wait for server recovery
                            error_text = await response.text()
                            logger.warning(f"🔧 Server unavailable for {link}, retrying in {wait_time}s (attempt {server_error_attempts}/{server_error_retries})")
                            logger.debug(f"503 Error details: {error_text}")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            logger.warning(f"⏭️  Server unavailable after {server_error_retries} retries, will retry in next cycle: {link}")
                            return {"link": link, "error": "server_unavailable", "status": "retry_next_cycle", "retry_count": server_error_attempts}
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed to unrestrict {link}: {response.status} - {error_text}")
                        return {"link": link, "error": error_text, "status": "failed_other", "http_status": response.status}
                        
            except Exception as e:
                logger.error(f"❌ Exception unrestricting {link}: {e}")
                return {"link": link, "error": str(e), "status": "exception"}
        
        # Should not reach here
        return {"link": link, "error": "unexpected_error", "status": "failed"}
    
    async def _enforce_rate_limit(self, endpoint_type: str = 'general'):
        """
        Enforce rate limiting for API calls based on endpoint type.
        
        Args:
            endpoint_type (str): 'general' or 'torrents'
        """
        current_time = time.time()
        
        if endpoint_type == 'torrents':
            request_times = self.torrents_request_times
            limit = self.torrents_rate_limit_per_minute
        else:
            request_times = self.general_request_times
            limit = self.general_rate_limit_per_minute

        # Remove requests older than 1 minute
        request_times = [t for t in request_times if current_time - t < 60]
        
        # If we're at the limit, wait
        if len(request_times) >= limit:
            wait_time = 60 - (current_time - request_times[0])
            if wait_time > 0:
                logger.info(f"⏱️  Rate limit for '{endpoint_type}' reached ({len(request_times)}/{limit}), waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                # Refresh request times after waiting
                current_time = time.time()
                request_times = [t for t in request_times if current_time - t < 60]
        
        # Add a small, consistent delay to smooth out requests
        delay_between_requests = 60.0 / limit
        if request_times:
            time_since_last = current_time - request_times[-1]
            if time_since_last < delay_between_requests:
                wait_time = delay_between_requests - time_since_last
                await asyncio.sleep(wait_time)
                current_time = time.time()
        
        # Add current request time
        request_times.append(current_time)

        # Update the correct list
        if endpoint_type == 'torrents':
            self.torrents_request_times = request_times
        else:
            self.general_request_times = request_times
    
    async def unrestrict_links_batch(self, links: List[str]) -> List[Dict]:
        """Unrestrict multiple links with batching and rate limiting"""
        
        logger.info(f"Unrestricting {len(links)} links with rate limiting...")
        
        # Create batches
        batches = [links[i:i + self.concurrency_limit] 
                  for i in range(0, len(links), self.concurrency_limit)]
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            for i, batch in enumerate(batches):
                logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} links)")
                batch_start_time = time.time()
                
                # Process batch concurrently
                batch_tasks = [self.unrestrict_link(session, link) for link in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Filter successful results
                for result in batch_results:
                    if isinstance(result, dict) and not isinstance(result, Exception):
                        results.append(result)
                
                # No need to manually wait here as _enforce_rate_limit handles it before each call
        
        logger.info(f"Completed unrestricting {len(results)} links")
        return results
    
    async def process_torrents_with_grouping(self, output_dir: Path) -> Dict:
        """Process torrents with proper grouping by torrent ID"""
        
        start_time = time.time()  # Track execution time
        
        # Create output directories
        torrents_file = output_dir / "realdebrid_torrents.json"
        unrestricted_file = output_dir / "realdebrid_unrestricted.json"
        
        # 1. Fetch torrents
        logger.info("📡 Step 1: Fetching ALL torrents with pagination...")
        torrents = await self.fetch_torrents()
        
        if not torrents:
            logger.error("❌ No torrents found")
            return {"success": False, "error": "No torrents found"}
        
        # Log pagination results
        downloaded_count = len([t for t in torrents if t.get('status') == 'downloaded'])
        logger.info(f"🎉 Pagination Complete:")
        logger.info(f"   📊 Total torrents: {len(torrents)}")
        logger.info(f"   ✅ Downloaded: {downloaded_count}")
        logger.info(f"   ⏳ Others: {len(torrents) - downloaded_count}")
        
        # Save torrents
        with open(torrents_file, 'w', encoding='utf-8') as f:
            json.dump(torrents, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved {len(torrents)} torrents to {torrents_file}")
        
        # 2. Collect all links from downloaded torrents
        logger.info("Step 2: Collecting links from downloaded torrents...")
        all_links = []
        torrent_link_map = {}  # Map link to torrent info
        
        for torrent in torrents:
            if torrent.get('status') == 'downloaded' and torrent.get('links'):
                torrent_id = torrent.get('id')
                torrent_name = torrent.get('filename', f"torrent_{torrent_id}")
                
                for link in torrent['links']:
                    if link.startswith('https://real-debrid.com/d/'):
                        all_links.append(link)
                        torrent_link_map[link] = {
                            'torrent_id': torrent_id,
                            'torrent_name': torrent_name
                        }
        
        logger.info(f"Found {len(all_links)} links from {len([t for t in torrents if t.get('status') == 'downloaded'])} downloaded torrents")
        
        # 3. Load existing unrestricted data if available
        existing_results = []
        if unrestricted_file.exists():
            try:
                with open(unrestricted_file, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)
                logger.info(f"Loaded {len(existing_results)} existing unrestricted results")
            except Exception as e:
                logger.error(f"Error loading existing unrestricted data: {e}")
        
        # 4. Find new links to unrestrict
        existing_links = {r['link'] for r in existing_results if 'link' in r}
        new_links = [link for link in all_links if link not in existing_links]
        
        logger.info(f"Need to unrestrict {len(new_links)} new links")
        
        # 5. Unrestrict new links
        if new_links:
            new_results = await self.unrestrict_links_batch(new_links)
            all_results = existing_results + new_results
        else:
            all_results = existing_results
        
        # Save unrestricted data
        with open(unrestricted_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(all_results)} unrestricted results")
        
        # 6. Create links.txt for compatibility
        links_file = output_dir / "realdebrid_links.txt"
        valid_links = []
        for result in all_results:
            if result.get('result', {}).get('download'):
                valid_links.append(result['result']['download'])
        
        with open(links_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_links))
        logger.info(f"Saved {len(valid_links)} direct links to {links_file}")
        
        # Generate summary with detailed error breakdown
        failed_unrestricts = [r for r in all_results if 'error' in r]
        rate_limit_errors = [r for r in failed_unrestricts if r.get('error') == 'rate_limit_exceeded']
        server_errors = [r for r in failed_unrestricts if r.get('error') == 'server_unavailable']
        other_errors = [r for r in failed_unrestricts if r not in rate_limit_errors and r not in server_errors]
        
        # Estimate pages based on total torrents (assuming ~100 per page)
        estimated_pages = (len(torrents) // 100) + 1 if len(torrents) % 100 != 0 else (len(torrents) // 100)
        
        summary = {
            "success": True,
            "source": "real_debrid_api", 
            "pagination": {
                "estimated_pages": estimated_pages,
                "total_torrents": len(torrents),
                "downloaded_torrents": downloaded_count,
            },
            "unrestrict_results": {
                "total_links": len(all_links),
                "successful": len([r for r in all_results if 'result' in r]),
                "failed": len(failed_unrestricts),
                "errors": {
                    "rate_limit_errors": len(rate_limit_errors),
                    "server_unavailable": len(server_errors), 
                    "other_errors": len(other_errors)
                }
            },
            "execution_time": time.time() - start_time
        }
        
        # Enhanced logging
        logger.info(f"🎉 Processing Complete!")
        logger.info(f"   📊 Pagination: ~{summary['pagination']['estimated_pages']} pages, {summary['pagination']['total_torrents']} torrents")
        logger.info(f"   🔗 Unrestrict: {summary['unrestrict_results']['successful']}/{summary['unrestrict_results']['total_links']} successful")
        if summary['unrestrict_results']['failed'] > 0:
            logger.info(f"   ❌ Errors:")
            logger.info(f"      ⏱️  Rate limits: {summary['unrestrict_results']['errors']['rate_limit_errors']}")
            logger.info(f"      🔧 Server issues: {summary['unrestrict_results']['errors']['server_unavailable']}")
            logger.info(f"      ❓ Other: {summary['unrestrict_results']['errors']['other_errors']}")
        logger.info(f"   ⏱️  Total time: {summary['execution_time']:.1f}s")
        
        return summary 