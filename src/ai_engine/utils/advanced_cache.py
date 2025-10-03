import hashlib
import json
from typing import Any, Optional, Dict, List, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
from numpy.typing import NDArray

try:
    import torch  # type: ignore
except ImportError:
    torch = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore
import logging
from ai_engine.core.config import config, settings

logger = logging.getLogger(__name__)

class SemanticCacheManager:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._embeddings: Dict[str, NDArray[np.float32]] = {}
        self._embedding_model = None
        self.max_cache_size = config.cache_max_size
        
        if config.use_embedding_cache:
            self._initialize_embedding_model()
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer for semantic similarity"""
        if SentenceTransformer is None:
            logger.warning("SentenceTransformer is not installed. Disabling embedding cache.")
            config.use_embedding_cache = False
            return

        try:
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Semantic embedding model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}. Falling back to exact matching.")
            config.use_embedding_cache = False
    
    def get_similar(self, text: str, cache_type: str, similarity_threshold: float = None) -> Optional[Any]:
        """Get cached result for semantically similar text"""
        if not config.cache_enabled:
            return None
            
        similarity_threshold = similarity_threshold or config.similarity_threshold
        
        try:
            # Try exact match first (fastest)
            exact_key = self._generate_exact_key(text, cache_type)
            exact_result = self._get_by_key(exact_key)
            if exact_result:
                logger.debug("Cache hit: exact match")
                return exact_result
            
            # Try semantic similarity if enabled
            if config.use_embedding_cache and self._embedding_model:
                similar_result = self._find_similar_cached(text, cache_type, similarity_threshold)
                if similar_result:
                    logger.debug("Cache hit: semantic similarity")
                    return similar_result
            
            logger.debug("Cache miss")
            return None
            
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None
    
    def set(self, text: str, cache_type: str, value: Any, ttl_minutes: int = None):
        """Store value in cache with semantic indexing"""
        if not config.cache_enabled:
            return
            
        try:
            ttl_minutes = ttl_minutes or config.cache_ttl_comment_minutes
            expiry_time = datetime.now() + timedelta(minutes=ttl_minutes)
            
            cache_key = self._generate_exact_key(text, cache_type)
            
            # Store in main cache
            self._cache[cache_key] = {
                "value": value,
                "text": text,
                "cache_type": cache_type,
                "created_at": datetime.now().isoformat(),
                "expires_at": expiry_time.isoformat(),
                "access_count": 0
            }
            
            # Generate and store embedding if enabled
            if config.use_embedding_cache and self._embedding_model:
                try:
                    embedding = self._embedding_model.encode(text)
                    self._embeddings[cache_key] = embedding
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {e}")
            
            # Clean up if cache is too large
            self._cleanup_if_needed()
            
            logger.debug(f"Cached: {cache_type} - {len(text)} chars")
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def _find_similar_cached(self, text: str, cache_type: str, threshold: float) -> Optional[Any]:
        """Find semantically similar cached content"""
        try:
            query_embedding = self._embedding_model.encode(text)
            if torch is not None and isinstance(query_embedding, torch.Tensor):
                query_embedding = query_embedding.cpu().numpy()
            best_match = None
            best_similarity = 0.0
            
            for cache_key, cache_data in self._cache.items():
                if cache_data["cache_type"] != cache_type:
                    continue
                    
                if self._is_expired(cache_data):
                    continue
                    
                if cache_key not in self._embeddings:
                    continue
                
                # Calculate cosine similarity
                cached_embedding = self._embeddings[cache_key]
                similarity = np.dot(query_embedding, cached_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding)
                )
                
                if similarity > threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cache_data
            
            if best_match:
                # Update access count
                best_match["access_count"] += 1
                logger.info(f"Semantic match found: similarity {best_similarity:.3f}")
                return best_match["value"]
                
            return None
            
        except Exception as e:
            logger.error(f"Semantic similarity search error: {e}")
            return None
    
    def _generate_exact_key(self, text: str, cache_type: str) -> str:
        """Generate exact cache key"""
        content = f"{cache_type}:{text.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_by_key(self, key: str) -> Optional[Any]:
        """Get cached value by exact key"""
        if key not in self._cache:
            return None
            
        cache_data = self._cache[key]
        
        if self._is_expired(cache_data):
            self._remove_key(key)
            return None
            
        cache_data["access_count"] += 1
        return cache_data["value"]
    
    def _is_expired(self, cache_data: Dict) -> bool:
        """Check if cache data is expired"""
        expires_at = datetime.fromisoformat(cache_data["expires_at"])
        return datetime.now() > expires_at
    
    def _remove_key(self, key: str):
        """Remove key from cache and embeddings"""
        self._cache.pop(key, None)
        self._embeddings.pop(key, None)
    
    def _cleanup_if_needed(self):
        """Clean up cache if it exceeds max size"""
        if len(self._cache) <= self.max_cache_size:
            return
            
        # Remove expired items first
        expired_keys = [
            key for key, data in self._cache.items() 
            if self._is_expired(data)
        ]
        
        for key in expired_keys:
            self._remove_key(key)
        
        # If still too large, remove least accessed items
        if len(self._cache) > self.max_cache_size:
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: (x[1]["access_count"], x[1]["created_at"])
            )
            
            items_to_remove = len(self._cache) - self.max_cache_size
            for key, _ in sorted_items[:items_to_remove]:
                self._remove_key(key)
        
        logger.info(f"Cache cleanup completed. Size: {len(self._cache)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._cache:
            return {"size": 0, "embedding_enabled": config.use_embedding_cache}
        
        total_access = sum(data["access_count"] for data in self._cache.values())
        cache_types = {}
        
        for data in self._cache.values():
            cache_type = data["cache_type"]
            cache_types[cache_type] = cache_types.get(cache_type, 0) + 1
        
        return {
            "size": len(self._cache),
            "total_accesses": total_access,
            "embedding_enabled": config.use_embedding_cache,
            "embedding_count": len(self._embeddings),
            "cache_types": cache_types,
            "max_size": self.max_cache_size
        }