"""
Comment Generator Module
Generates professional Jira comments from casual user updates
"""

import hashlib
import logging
from typing import Dict, Any, Optional

from ..models.model_manager import ModelManager
from ..prompts.system_prompts import SystemPrompts
from ..utils.cache import CacheManager
from ..core.config import config

logger = logging.getLogger(__name__)


class CommentGenerator:
    """
    Generates professional Jira comments from casual user updates
    with caching and quality assessment
    """
    
    def __init__(
        self, 
        model_manager: Optional[ModelManager] = None,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Initialize comment generator
        
        Args:
            model_manager: Optional model manager instance (for shared metrics)
            cache_manager: Optional cache manager instance (for shared caching)
        """
        self.model_manager = model_manager or ModelManager()
        self.cache_manager = cache_manager or CacheManager()
        self.prompts = SystemPrompts()
        
        logger.info("CommentGenerator initialized")
    
    def generate_professional_comment(
        self, 
        user_update: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert casual user update to professional Jira comment
        
        Args:
            user_update: Raw user input
            context: Additional context (task info, user role, etc.)
        
        Returns:
            Dict with generated comment and metadata
        """
        try:
            # Validate input
            if not user_update or not user_update.strip():
                return {
                    "success": False,
                    "error": "empty_input",
                    "error_message": "User update cannot be empty"
                }
            
            # Truncate if too long
            if len(user_update) > config.max_input_length:
                logger.warning(f"Input too long ({len(user_update)} chars), truncating")
                user_update = user_update[:config.max_input_length]
            
            # Check cache first
            cache_key = self._generate_cache_key(user_update)
            
            if config.cache_enabled:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result:
                    logger.info("Using cached comment rephrasing")
                    cached_result['from_cache'] = True
                    cached_result['cache_timestamp'] = self._get_timestamp()
                    return cached_result
            
            # Build context-aware prompt using SystemPrompts helper
            system_prompt = self._build_system_prompt(context)
            user_message = f"User update: {user_update}"
            
            # Generate using OpenAI with cost check
            llm_response = self.model_manager.generate_completion_with_cost_check(
                system_prompt=system_prompt,
                user_message=user_message,
                model_type="primary",  # Use best model for professional tone
                temperature=0.2  # Low temperature for consistent professional tone
            )
            
            if not llm_response["success"]:
                return self._handle_generation_error(user_update, llm_response)
            
            # Process and validate the response
            professional_comment = llm_response["content"].strip()
            
            # Validate response is not empty
            if not professional_comment:
                logger.error("LLM returned empty response")
                return self._handle_generation_error(
                    user_update,
                    {"error": "empty_response", "fallback_available": True}
                )
            
            # Quality checks
            quality_score = self._assess_comment_quality(professional_comment, user_update)
            
            result = {
                "success": True,
                "original_update": user_update,
                "professional_comment": professional_comment,
                "quality_score": quality_score,
                "requires_approval": quality_score < config.auto_approval_threshold,
                "word_count": len(professional_comment.split()),
                "processing_metadata": {
                    "model_used": llm_response.get("model_used"),
                    "tokens_used": llm_response.get("usage", {}).get("total_tokens"),
                    "temperature": 0.2,
                    "cached": False,
                    "processing_time": llm_response.get("metadata", {}).get("processing_time_seconds")
                },
                "from_cache": False
            }
            
            # Cache if high quality
            if config.cache_enabled and quality_score >= config.quality_threshold:
                try:
                    self.cache_manager.set(
                        cache_key, 
                        result, 
                        ttl_minutes=config.cache_ttl_comment_minutes
                    )
                    logger.debug(f"Cached comment with quality score {quality_score:.2f}")
                except Exception as e:
                    logger.warning(f"Failed to cache comment: {e}")
            
            logger.info(f"Generated professional comment (quality: {quality_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error generating professional comment: {str(e)}", exc_info=True)
            return self._create_fallback_response(user_update, str(e))
    
    def _build_system_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """
        Build context-aware system prompt using SystemPrompts helper
        
        Args:
            context: User context (role, project, task type)
            
        Returns:
            System prompt with optional context
        """
        if not context:
            return self.prompts.JIRA_COMMENT_REPHRASER
        
        # Use SystemPrompts helper method for context-aware prompts
        return SystemPrompts.build_comment_prompt_with_context(
            user_role=context.get("user_role"),
            project_type=context.get("project_type"),
            task_type=context.get("task_info", {}).get("type")
        )
    
    def _generate_cache_key(self, user_update: str) -> str:
        """
        Generate deterministic cache key for user update
        
        Args:
            user_update: User's message
            
        Returns:
            Cache key string
        """
        # Normalize input
        normalized = user_update.lower().strip()[:200]
        
        # Use MD5 for deterministic hashing
        content_hash = hashlib.md5(normalized.encode('utf-8')).hexdigest()[:16]
        
        return f"comment:{content_hash}"
    
    def _assess_comment_quality(self, generated_comment: str, original_update: str) -> float:
        """
        Assess quality of generated comment using heuristics
        Returns score between 0.0 and 1.0
        
        Args:
            generated_comment: AI-generated comment
            original_update: Original user input
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 1.0
        
        # Length checks
        word_count = len(generated_comment.split())
        if word_count < 3:
            score -= 0.4  # Too short
        elif word_count > 100:
            score -= 0.2  # Too long
        
        # Professional tone indicators
        professional_words = [
            'completed', 'implemented', 'resolved', 'pending', 
            'reviewing', 'investigating', 'deployment', 'testing'
        ]
        casual_words = [
            'done', 'finished', 'gonna', 'wanna', 'kinda', 
            'yeah', 'nope', 'cool', 'awesome'
        ]
        
        comment_lower = generated_comment.lower()
        
        prof_count = sum(1 for word in professional_words if word in comment_lower)
        casual_count = sum(1 for word in casual_words if word in comment_lower)
        
        if prof_count > casual_count:
            score += 0.1  # Bonus for professional tone
        elif casual_count > prof_count:
            score -= 0.3  # Penalty for casual tone
        
        # Check if it preserves key information
        # Extract technical keywords from original
        original_words = set(original_update.lower().split())
        generated_words = set(generated_comment.lower().split())
        
        # Technical terms that should be preserved
        technical_terms = {
            'api', 'bug', 'feature', 'database', 'frontend', 
            'backend', 'staging', 'production', 'test', 'deployment'
        }
        
        original_tech = original_words.intersection(technical_terms)
        preserved_tech = original_tech.intersection(generated_words)
        
        if original_tech and len(preserved_tech) / len(original_tech) < 0.5:
            score -= 0.2  # Lost important technical terms
        
        # Ensure score is between 0.0 and 1.0
        return max(0.0, min(1.0, score))
    
    def _handle_generation_error(self, user_update: str, llm_response: Dict) -> Dict:
        """
        Handle LLM generation errors with fallbacks
        
        Args:
            user_update: Original user input
            llm_response: Failed LLM response
            
        Returns:
            Fallback response dict
        """
        if llm_response.get("fallback_available"):
            # Try simple rephrasing rules
            simple_rephrase = self._simple_rephrase_fallback(user_update)
            
            logger.info("Using simple rephrase fallback")
            
            return {
                "success": True,
                "original_update": user_update,
                "professional_comment": simple_rephrase,
                "quality_score": 0.6,
                "requires_approval": True,  # Always require approval for fallbacks
                "fallback_used": True,
                "error_reason": llm_response.get("error", "unknown"),
                "word_count": len(simple_rephrase.split()),
                "processing_metadata": {
                    "fallback_type": "simple_rephrase"
                }
            }
        
        return self._create_fallback_response(
            user_update, 
            llm_response.get("error_message", "Generation failed")
        )
    
    def _simple_rephrase_fallback(self, user_update: str) -> str:
        """
        Simple rule-based rephrasing as fallback when LLM fails
        
        Args:
            user_update: Original user input
            
        Returns:
            Basic cleaned-up version of input
        """
        # Basic cleanup
        cleaned = user_update.strip()
        
        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # Add period if missing
        if cleaned and cleaned[-1] not in '.!?':
            cleaned += '.'
        
        # Simple replacements for common contractions
        replacements = {
            " i ": " I ",
            " im ": " I'm ",
            " ive ": " I've ",
            " dont ": " don't ",
            " cant ": " can't ",
            " wont ": " won't ",
            " didnt ": " didn't "
        }
        
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        return f"Update: {cleaned}"
    
    def _create_fallback_response(self, user_update: str, error_msg: str) -> Dict:
        """
        Create fallback response when everything fails
        
        Args:
            user_update: Original user input
            error_msg: Error message
            
        Returns:
            Error response dict
        """
        return {
            "success": False,
            "original_update": user_update,
            "error": "generation_failed",
            "error_message": error_msg,
            "suggested_action": "manual_review",
            "fallback_comment": f"Task update: {user_update}"
        }
    
    def _get_timestamp(self) -> str:
        """Get current UTC timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()