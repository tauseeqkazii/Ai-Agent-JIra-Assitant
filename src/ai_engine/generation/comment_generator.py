from typing import Dict, Any, Optional
import logging
from ..models.model_manager import ModelManager
from ..prompts.system_prompts import SystemPrompts
from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)

class CommentGenerator:
    """Generates professional Jira comments from casual user updates"""
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager or ModelManager()
        self.cache_manager = CacheManager()
        self.prompts = SystemPrompts()
    
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
            # Check cache first
            cache_key = f"comment_rephrase:{hash(user_update.lower())}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.info("Using cached comment rephrasing")
                return cached_result
            
            # Build context-aware prompt
            system_prompt = self._build_context_prompt(context)
            user_message = f"User update: {user_update}"
            
            # Generate using OpenAI
            llm_response = self.model_manager.generate_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                model_type="primary",  # Use best model for professional tone
                temperature=0.2  # Low temperature for consistent professional tone
            )
            
            if not llm_response["success"]:
                return self._handle_generation_error(user_update, llm_response)
            
            # Process and validate the response
            professional_comment = llm_response["content"].strip()
            
            # Quality checks
            quality_score = self._assess_comment_quality(professional_comment, user_update)
            
            result = {
                "success": True,
                "original_update": user_update,
                "professional_comment": professional_comment,
                "quality_score": quality_score,
                "requires_approval": quality_score < 0.8,  # Flag for user review if low quality
                "word_count": len(professional_comment.split()),
                "processing_metadata": {
                    "model_used": llm_response["model_used"],
                    "tokens_used": llm_response["usage"]["total_tokens"],
                    "temperature": 0.2,
                    "cached": False
                }
            }
            
            # Cache if high quality
            if quality_score >= 0.8:
                self.cache_manager.set(cache_key, result, ttl_minutes=1440)  # 24 hours
            
            logger.info(f"Generated professional comment (quality: {quality_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error generating professional comment: {str(e)}")
            return self._create_fallback_response(user_update, str(e))
    
    def _build_context_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context-aware system prompt"""
        base_prompt = self.prompts.JIRA_COMMENT_REPHRASER
        
        if not context:
            return base_prompt
        
        # Add context-specific instructions
        additions = []
        
        if context.get("user_role"):
            additions.append(f"User role: {context['user_role']}")
            
        if context.get("project_type"):
            additions.append(f"Project context: {context['project_type']}")
            
        if context.get("task_type"):
            additions.append(f"Task type: {context['task_type']}")
        
        if additions:
            context_info = "\nAdditional context:\n" + "\n".join(additions)
            return base_prompt + context_info
        
        return base_prompt
    
    def _assess_comment_quality(self, generated_comment: str, original_update: str) -> float:
        """
        Assess quality of generated comment
        Returns score between 0.0 and 1.0
        """
        score = 1.0
        
        # Length checks
        if len(generated_comment) < 10:
            score -= 0.3
        elif len(generated_comment) > 300:
            score -= 0.1
        
        # Professional tone indicators
        professional_words = ['completed', 'implemented', 'resolved', 'pending', 'reviewing']
        casual_words = ['done', 'finished', 'gonna', 'wanna', 'kinda']
        
        prof_count = sum(1 for word in professional_words if word in generated_comment.lower())
        casual_count = sum(1 for word in casual_words if word in generated_comment.lower())
        
        if prof_count > casual_count:
            score += 0.1
        elif casual_count > prof_count:
            score -= 0.2
        
        # Check if it preserves original meaning (simple keyword overlap)
        original_words = set(original_update.lower().split())
        generated_words = set(generated_comment.lower().split())
        
        # Should preserve key technical terms
        technical_words = original_words.intersection(generated_words)
        if len(technical_words) / max(len(original_words), 1) < 0.3:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _handle_generation_error(self, user_update: str, llm_response: Dict) -> Dict:
        """Handle LLM generation errors with fallbacks"""
        if llm_response.get("fallback_available"):
            # Try simpler rephrasing rules
            simple_rephrase = self._simple_rephrase_fallback(user_update)
            return {
                "success": True,
                "original_update": user_update,
                "professional_comment": simple_rephrase,
                "quality_score": 0.6,
                "requires_approval": True,  # Always require approval for fallbacks
                "fallback_used": True,
                "error_reason": llm_response.get("error", "unknown")
            }
        
        return self._create_fallback_response(user_update, llm_response.get("error_message", "Generation failed"))
    
    def _simple_rephrase_fallback(self, user_update: str) -> str:
        """Simple rule-based rephrasing as fallback"""
        # Basic cleanup
        cleaned = user_update.strip()
        
        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # Add period if missing
        if cleaned and cleaned[-1] not in '.!?':
            cleaned += '.'
        
        # Simple replacements
        replacements = {
            " i ": " I ",
            " im ": " I'm ",
            " ive ": " I've ",
            " dont ": " don't ",
            " cant ": " can't ",
            " wont ": " won't "
        }
        
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        return f"Update: {cleaned}"
    
    def _create_fallback_response(self, user_update: str, error_msg: str) -> Dict:
        """Create fallback response when everything fails"""
        return {
            "success": False,
            "original_update": user_update,
            "error": "generation_failed",
            "error_message": error_msg,
            "suggested_action": "manual_review",
            "fallback_comment": f"Task update: {user_update}"
        }