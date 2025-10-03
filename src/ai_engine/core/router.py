from typing import Dict, Any, Optional
import logging
from ..classification.intent_classifier import IntentClassifier, RouteType, ClassificationResult
from ..utils.cache import CacheManager
from ..utils.metrics import MetricsCollector
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskRouter:
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.intent_classifier = IntentClassifier()
        self.cache_manager = cache_manager or CacheManager()
        self.metrics = MetricsCollector()
        
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
            # Step 1: Classify the intent
            classification = self.intent_classifier.classify(user_input)
            
            # Step 2: Check cache for similar requests (if applicable)
            cache_key = self._generate_cache_key(user_input, classification.route_type)
            cached_result = self.cache_manager.get(cache_key)
            
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
                "cached_result": cached_result,
                "processing_metadata": {
                    "timestamp": self._get_timestamp(),
                    "user_id": user_context.get("user_id"),
                    "session_id": user_context.get("session_id")
                }
            }
            
            # Step 4: Log metrics like which user costing us more money etc.
            self.metrics.record_classification(
                route_type=classification.route_type.value,
                confidence=classification.confidence,
                user_id=user_context.get("user_id")
            )
            
            logger.info(f"Routed request: {classification.route_type.value} (confidence: {classification.confidence})")
            return routing_response
            
        except Exception as e:
            logger.error(f"Routing error: {str(e)}")
            # Fallback to LLM classification on any error
            return self._create_fallback_response(user_input, user_context, str(e))
    
    def _requires_llm(self, route_type: RouteType) -> bool:
        """Determine if this route requires LLM processing"""
        llm_routes = {
            RouteType.LLM_REPHRASING,
            RouteType.LLM_EMAIL, 
            RouteType.LLM_CLASSIFICATION
        }
        return route_type in llm_routes
    
    def _generate_cache_key(self, user_input: str, route_type: RouteType) -> str:
        """Generate cache key for similar requests"""
        # Simple approach - use first 50 chars + route type
        input_hash = hash(user_input.lower().strip()[:50])
        return f"route:{route_type.value}:{abs(input_hash)}"
    
    def _create_fallback_response(self, user_input: str, user_context: Dict, error: str) -> Dict:
        """Create fallback response when classification fails"""
        return {
            "route_type": RouteType.LLM_CLASSIFICATION.value,
            "confidence": 0.5,
            "requires_llm": True,
            "user_input": user_input,
            "user_context": user_context,
            "error": error,
            "fallback": True,
            "processing_metadata": {
                "timestamp": self._get_timestamp(),
                "user_id": user_context.get("user_id"),
                "session_id": user_context.get("session_id")
            }
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.utcnow().isoformat()