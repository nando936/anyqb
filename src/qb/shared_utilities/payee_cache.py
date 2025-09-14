"""
Simple cache for payee data to avoid repeated QuickBooks queries
"""

import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class PayeeCache:
    """Cache for payee data with TTL"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        """Initialize cache with time-to-live in seconds"""
        self.cache = {}
        self.ttl = ttl_seconds
        self.last_full_search = None
        self.full_search_cache = []
    
    def get(self, key: str) -> Optional[List[Dict]]:
        """Get cached value if not expired"""
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit for key: {key}")
                return cached_data
            else:
                # Expired, remove from cache
                del self.cache[key]
                logger.debug(f"Cache expired for key: {key}")
        return None
    
    def set(self, key: str, value: List[Dict]):
        """Set cache value with current timestamp"""
        self.cache[key] = (value, time.time())
        logger.debug(f"Cached {len(value)} items for key: {key}")
    
    def get_full_search(self) -> Optional[List[Dict]]:
        """Get cached full search results if not expired"""
        if self.last_full_search:
            if time.time() - self.last_full_search < self.ttl:
                logger.debug(f"Cache hit for full search ({len(self.full_search_cache)} items)")
                return self.full_search_cache
            else:
                self.last_full_search = None
                self.full_search_cache = []
                logger.debug("Full search cache expired")
        return None
    
    def set_full_search(self, value: List[Dict]):
        """Cache full search results"""
        self.full_search_cache = value
        self.last_full_search = time.time()
        logger.debug(f"Cached full search with {len(value)} items")
    
    def clear(self):
        """Clear all cached data"""
        self.cache.clear()
        self.last_full_search = None
        self.full_search_cache = []
        logger.debug("Cache cleared")

# Global cache instance
payee_cache = PayeeCache(ttl_seconds=1800)  # 30 minute cache