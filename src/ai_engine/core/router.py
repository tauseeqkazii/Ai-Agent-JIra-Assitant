"""
Task Router Module
Routes user requests to appropriate handlers (backend vs LLM)
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..classification.intent_classifier import IntentClassifier, RouteType, ClassificationResult
from ..utils.cache import CacheManager
from ..utils.metrics import MetricsCollector
from ..core.config import config

logger = logging.getLogger(__name__)


class TaskRouter:
    """
    Routes user requests based on intent classification
    Decides between backend shortcuts and LLM processing
    """
    
    def __init__(
        self, 
        cache_manager: Optional[CacheManager] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        """
        Initialize router with optional dependency injection
        
        Args:
            cache_manager: Optional cache manager instance (for shared caching)
            metrics: Optional metrics collector instance (for shared metrics)
        """
        self.intent_classifier = IntentClassifier()
        self.cache_manager = cache_manager or CacheManager()
        self.metrics = metrics or MetricsCollector()
        
        logger.info("TaskRouter initialized")
        
    def route_request(self, user_input: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main routing method - decides whether to use backend shortcuts or LLM
        
        Args:
            user_input: Raw user message
            user_context: User info (id, current tasks, etc.)
            
        Returns:
            Dict with routing decision and metadata
        """
        try:
            
            scope_check = self.intent_classifier.is_within_scope(user_input)
            
            if not scope_check["in_scope"]:
                logger.info(f"Input out of scope: {scope_check['reason']}")
                return {
                    "route_type": "out_of_scope",
                    "confidence": 0.95,
                    "requires_llm": False,
                    "user_input": user_input,
                    "user_context": user_context,
                    "out_of_scope_reason": scope_check["reason"],
                    "suggested_response": scope_check.get(
                        "suggestion",
                        "This request is outside my scope. I can only rephrase Jira task updates or generate professional emails."
                    ),
                    "processing_metadata": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "user_id": user_context.get("user_id"),
                    },
                    "backend_action": "show_scope_message"
                }
            # Validate inputs
            if not user_input or not user_input.strip():
                logger.warning("Empty input received in router")
                return self._create_error_response(
                    "empty_input",
                    "Please provide a message",
                    user_input,
                    user_context
                )
            
            if not user_context:
                user_context = {}
                logger.warning("No user context provided, using empty dict")
            
            # Step 1: Classify the intent
            classification = self.intent_classifier.classify(user_input)
            
            logger.debug(
                f"Classified as {classification.route_type.value} "
                f"with confidence {classification.confidence:.2f}"
            )
            
            # Step 2: Check cache for similar requests (if confidence is high)
            cache_key = self._generate_cache_key(user_input, classification.route_type)
            cached_result = None
            
            if config.cache_enabled and classification.confidence >= config.confidence_threshold:
                cached_result = self.cache_manager.get(cache_key)
                
                if cached_result:
                    logger.info("Cache hit for routing decision")
                    # Add cache hit indicator
                    cached_result['from_cache'] = True
                    cached_result['cache_timestamp'] = datetime.utcnow().isoformat()
                    return cached_result
            
            # Step 3: Build routing response
            routing_response = {
                "route_type": classification.route_type.value,
                "confidence": classification.confidence,
                "requires_llm": self._requires_llm(classification.route_type),
                "user_input": user_input,
                "user_context": user_context,
                "classification_details": {
                    "matched_pattern": classification.matched_pattern,
                    "extracted_entities": self.intent_classifier.extract_task_info(user_input)
                },
                "processing_metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_context.get("user_id"),
                    "session_id": user_context.get("session_id"),
                    "router_version": "2.0"
                },
                "from_cache": False
            }
            
            # Step 4: Cache the result if confidence is high
            if config.cache_enabled and classification.confidence >= config.confidence_threshold:
                try:
                    self.cache_manager.set(
                        cache_key, 
                        routing_response, 
                        ttl_minutes=config.cache_ttl_routing_minutes
                    )
                    logger.debug(f"Cached routing result for key: {cache_key[:16]}...")
                except Exception as e:
                    logger.warning(f"Failed to cache routing result: {e}")
                    # Continue without caching - don't fail the request
            
            # Step 5: Log metrics
            try:
                self.metrics.record_classification(
                    route_type=classification.route_type.value,
                    confidence=classification.confidence,
                    user_id=user_context.get("user_id", "unknown")
                )
            except Exception as e:
                logger.warning(f"Failed to record classification metrics: {e}")
                # Continue without metrics - don't fail the request
            
            logger.info(
                f"Routed request: {classification.route_type.value} "
                f"(confidence: {classification.confidence:.2f})"
            )
            
            return routing_response
            
        except Exception as e:
            logger.error(f"Routing error: {str(e)}", exc_info=True)
            # Fallback to LLM classification on any error
            return self._create_fallback_response(user_input, user_context, str(e))
    
    def _requires_llm(self, route_type: RouteType) -> bool:
        """
        Determine if this route requires LLM processing
        
        Args:
            route_type: The classified route type
            
        Returns:
            True if LLM processing is needed
        """
        llm_routes = {
            RouteType.LLM_REPHRASING,
            RouteType.LLM_EMAIL, 
            RouteType.LLM_CLASSIFICATION
        }
        return route_type in llm_routes
    
    def _generate_cache_key(self, user_input: str, route_type: RouteType) -> str:
        """
        Generate deterministic cache key using MD5 hash
        
        Args:
            user_input: User's message
            route_type: Classified route type
            
        Returns:
            Cache key string
        """
        # Normalize input for consistent caching
        normalized = user_input.lower().strip()[:200]  # Limit to 200 chars
        
        # Create content to hash
        content = f"{route_type.value}:{normalized}"
        
        # Use MD5 for deterministic hashing (fixed from built-in hash())
        hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
        
        return f"route:{route_type.value}:{hash_value}"
    
    def _create_error_response(
        self, 
        error_type: str, 
        error_message: str,
        user_input: str,
        user_context: Dict
    ) -> Dict:
        """
        Create error response for invalid input
        
        Args:
            error_type: Type of error
            error_message: Human-readable error message
            user_input: Original user input
            user_context: User context
            
        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error": error_type,
            "error_message": error_message,
            "route_type": "error",
            "requires_llm": False,
            "user_input": user_input,
            "user_context": user_context,
            "processing_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_context.get("user_id", "unknown"),
                "session_id": user_context.get("session_id")
            }
        }
    
    def _create_fallback_response(
        self, 
        user_input: str, 
        user_context: Dict, 
        error: str
    ) -> Dict:
        """
        Create fallback response when classification fails
        
        Args:
            user_input: User's message
            user_context: User context
            error: Error message
            
        Returns:
            Fallback response routing to LLM classification
        """
        logger.warning(f"Creating fallback response due to error: {error}")
        
        return {
            "route_type": RouteType.LLM_CLASSIFICATION.value,
            "confidence": 0.5,
            "requires_llm": True,
            "user_input": user_input,
            "user_context": user_context,
            "error": error,
            "fallback": True,
            "processing_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_context.get("user_id", "unknown"),
                "session_id": user_context.get("session_id"),
                "error_details": error
            }
        }
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics for monitoring
        
        Returns:
            Dictionary with routing statistics
        """
        try:
            metrics_stats = self.metrics.get_stats()
            
            return {
                "total_routes": metrics_stats.get("total_classifications", 0),
                "route_distribution": metrics_stats.get("route_distribution", {}),
                "backend_shortcuts": metrics_stats.get("backend_shortcuts", 0),
                "llm_calls": metrics_stats.get("llm_calls", 0),
                "average_confidence": metrics_stats.get("average_confidence", 0.0),
                "cache_enabled": config.cache_enabled
            }
        except Exception as e:
            logger.error(f"Error getting routing stats: {e}")
            return {"error": "Failed to retrieve stats"}