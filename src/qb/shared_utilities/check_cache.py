"""
Quarter-based cache for check data to improve search performance
Caches previous quarter and current quarter checks
"""

import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pickle
import os

logger = logging.getLogger(__name__)

class CheckCache:
    """Cache for check data organized by quarters"""
    
    def __init__(self, cache_dir: str = "cache", ttl_seconds: int = 3600):
        """Initialize cache with directory and TTL (default 1 hour)"""
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        self.memory_cache = {}  # In-memory cache for current session
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
            except:
                pass
    
    def _get_quarter_key(self, date: datetime) -> str:
        """Get quarter key for a given date (e.g., '2024_Q3')"""
        quarter = (date.month - 1) // 3 + 1
        return f"{date.year}_Q{quarter}"
    
    def _get_quarter_dates(self, quarter_key: str) -> tuple:
        """Get start and end dates for a quarter key"""
        year, q = quarter_key.split('_Q')
        year = int(year)
        quarter = int(q)
        
        start_month = (quarter - 1) * 3 + 1
        start_date = datetime(year, start_month, 1)
        
        if quarter == 4:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, start_month + 3, 1) - timedelta(days=1)
        
        return start_date, end_date
    
    def get_current_quarter_key(self) -> str:
        """Get the current quarter key"""
        return self._get_quarter_key(datetime.now())
    
    def get_previous_quarter_key(self) -> str:
        """Get the previous quarter key"""
        now = datetime.now()
        three_months_ago = now - timedelta(days=90)
        return self._get_quarter_key(three_months_ago)
    
    def get_quarter_checks(self, quarter_key: str) -> Optional[List[Dict]]:
        """Get cached checks for a specific quarter"""
        # Check memory cache first
        if quarter_key in self.memory_cache:
            cached_data, timestamp = self.memory_cache[quarter_key]
            if time.time() - timestamp < self.ttl:
                logger.info(f"Memory cache hit for quarter {quarter_key}: {len(cached_data)} checks")
                return cached_data
            else:
                del self.memory_cache[quarter_key]
        
        # Check disk cache
        cache_file = os.path.join(self.cache_dir, f"checks_{quarter_key}.pkl")
        if os.path.exists(cache_file):
            try:
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < self.ttl:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    # Also store in memory cache
                    self.memory_cache[quarter_key] = (data, time.time())
                    logger.info(f"Disk cache hit for quarter {quarter_key}: {len(data)} checks")
                    return data
                else:
                    # Cache expired, delete file
                    os.remove(cache_file)
                    logger.info(f"Disk cache expired for quarter {quarter_key}")
            except Exception as e:
                logger.error(f"Error reading cache file: {e}")
        
        return None
    
    def set_quarter_checks(self, quarter_key: str, checks: List[Dict]):
        """Cache checks for a specific quarter"""
        # Store in memory cache
        self.memory_cache[quarter_key] = (checks, time.time())
        
        # Store on disk
        cache_file = os.path.join(self.cache_dir, f"checks_{quarter_key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(checks, f)
            logger.info(f"Cached {len(checks)} checks for quarter {quarter_key}")
        except Exception as e:
            logger.error(f"Error writing cache file: {e}")
    
    def get_recent_checks(self, days: int = 90) -> Optional[List[Dict]]:
        """Get cached recent checks by combining quarters"""
        all_checks = []
        
        # Get current and previous quarter
        current_q = self.get_current_quarter_key()
        prev_q = self.get_previous_quarter_key()
        
        # Get checks from both quarters
        for quarter_key in [prev_q, current_q]:
            quarter_checks = self.get_quarter_checks(quarter_key)
            if quarter_checks:
                all_checks.extend(quarter_checks)
        
        if all_checks:
            # Filter by date if needed
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = []
            for check in all_checks:
                check_date = check.get('date')
                if check_date:
                    if isinstance(check_date, str):
                        try:
                            check_date = datetime.fromisoformat(check_date.replace('+00:00', ''))
                        except:
                            continue
                    if check_date >= cutoff_date:
                        filtered.append(check)
            
            logger.info(f"Returning {len(filtered)} recent checks from cache")
            return filtered
        
        return None
    
    def clear(self):
        """Clear all cached data"""
        self.memory_cache.clear()
        
        # Clear disk cache
        try:
            for file in os.listdir(self.cache_dir):
                if file.startswith('checks_') and file.endswith('.pkl'):
                    os.remove(os.path.join(self.cache_dir, file))
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

# Global cache instance
check_cache = CheckCache(cache_dir="C:\\Users\\nando\\Projects\\anyQBMCP\\cache", ttl_seconds=3600)