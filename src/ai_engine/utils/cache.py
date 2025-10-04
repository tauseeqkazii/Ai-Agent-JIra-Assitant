"""
Cache Manager Module
Handles caching of AI responses with TTL and memory management
"""

import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from threading import Lock
from collections import OrderedDict
import logging

from ..core.config import config

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Thread-safe in-memory cache with TTL and LRU eviction
    Production note: Backend team should replace with Redis for distributed caching
    """
    
    def __init__(self, max_size: Optional[int] = None):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of cache entries (defaults to config value)
        """
        self._cache: OrderedDict[str, Dict] = OrderedDict()
        self._expiry: Dict[str, datetime] = {}
        self._lock = Lock()
        self.max_size = max_size or config.cache_max_size
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info(f"CacheManager initialized with max_size={self.max_size}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired (thread-safe)
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss: {key[:20]}...")
                return None
            
            # Check expiry
            if key in self._expiry and datetime.utcnow() >= self._expiry[key]:
                logger.debug(f"Cache expired: {key[:20]}...")
                self._remove(key)
                self._misses += 1
                return None
            
            # Move to end (LRU: most recently used)
            self._cache.move_to_end(key)
            
            self._hits += 1
            logger.debug(f"Cache hit: {key[:20]}...")
            return self._cache[key]
    
    def set(self, key: str, value: Any, ttl_minutes: int = 60):
        """
        Set cached value with TTL (thread-safe)
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_minutes: Time to live in minutes
        """
        with self._lock:
            # Evict oldest entry if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            # Store value and expiry
            self._cache[key] = value
            self._expiry[key] = datetime.utcnow() + timedelta(minutes=ttl_minutes)
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            logger.debug(f"Cached: {key[:20]}... (TTL: {ttl_minutes}m)")
    
    def clear(self, key: Optional[str] = None):
        """
        Clear specific key or entire cache (thread-safe)
        
        Args:
            key: Specific key to clear, or None to clear all
        """
        with self._lock:
            if key:
                self._remove(key)
                logger.debug(f"Cleared cache key: {key[:20]}...")
            else:
                count = len(self._cache)
                self._cache.clear()
                self._expiry.clear()
                logger.info(f"Cleared entire cache ({count} entries)")
    
    def _remove(self, key: str):
        """
        Remove key from cache and expiry (must be called within lock)
        
        Args:
            key: Cache key to remove
        """
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
    
    def _evict_oldest(self):
        """
        Evict the least recently used entry (must be called within lock)
        """
        if self._cache:
            # OrderedDict maintains insertion order
            # Oldest is first item (FIFO with move_to_end = LRU)
            oldest_key = next(iter(self._cache))
            self._remove(oldest_key)
            self._evictions += 1
            logger.debug(f"Evicted oldest entry: {oldest_key[:20]}...")
    
    def cleanup_expired(self):
        """
        Proactively remove expired entries (thread-safe)
        Call this periodically in production (e.g., every 5 minutes)
        """
        with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, expiry_time in self._expiry.items()
                if now >= expiry_time
            ]
            
            for key in expired_keys:
                self._remove(key)
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics (thread-safe)
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0.0,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 3),
                "evictions": self._evictions,
                "enabled": config.cache_enabled
            }
    
    def reset_stats(self):
        """Reset cache statistics (thread-safe)"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            logger.info("Cache statistics reset")


def generate_cache_key(prefix: str, content: str, max_length: int = 200) -> str:
    """
    Generate a deterministic cache key using MD5 hash
    
    Args:
        prefix: Key prefix (e.g., "comment", "email", "route")
        content: Content to hash
        max_length: Maximum content length to consider
        
    Returns:
        Cache key string
    """
    # Normalize content
    normalized = content.lower().strip()[:max_length]
    
    # Create hash
    content_hash = hashlib.md5(f"{prefix}:{normalized}".encode('utf-8')).hexdigest()[:16]
    
    return f"{prefix}:{content_hash}"