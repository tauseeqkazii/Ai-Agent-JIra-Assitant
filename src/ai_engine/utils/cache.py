from typing import Any, Optional
import json
import hashlib
from datetime import datetime, timedelta

class CacheManager:
    """Simple in-memory cache for development - backend team will implement Redis"""
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self._cache:
            if key not in self._expiry or datetime.now() < self._expiry[key]:
                return self._cache[key]
            else:
                # Expired - remove
                self._remove(key)
        return None
    
    def set(self, key: str, value: Any, ttl_minutes: int = 60):
        """Set cached value with TTL"""
        self._cache[key] = value
        self._expiry[key] = datetime.now() + timedelta(minutes=ttl_minutes)
    
    def _remove(self, key: str):
        """Remove from cache"""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)