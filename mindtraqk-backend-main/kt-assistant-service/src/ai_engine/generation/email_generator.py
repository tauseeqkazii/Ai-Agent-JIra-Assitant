"""
Email Generator Module
Generates professional emails based on user requests
"""

import hashlib
import re
import logging
from typing import Dict, Any, Optional

from ..models.model_manager import ModelManager
from ..prompts.system_prompts import SystemPrompts
from ..utils.cache import CacheManager
from ..core.config import config

logger = logging.getLogger(__name__)


class EmailGenerator:
    """
    Generates professional emails based on user requests
    with caching and security validation
    """
    
    def __init__(
        self, 
        model_manager: Optional[ModelManager] = None,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Initialize email generator
        
        Args:
            model_manager: Optional model manager instance (for shared metrics)
            cache_manager: Optional cache manager instance (for shared caching)
        """
        self.model_manager = model_manager or ModelManager()
        self.cache_manager = cache_manager or CacheManager()
        self.prompts = SystemPrompts()
        
        logger.info("EmailGenerator initialized")
    
    def generate_email(
        self, 
        email_request: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate professional email based on user request
        
        Args:
            email_request: User's email request
            user_context: User info (name, manager, etc.)
        
        Returns:
            Dict with generated email and metadata
        """
        try:
            # Validate input
            if not email_request or not email_request.strip():
                return {
                    "success": False,
                    "error": "empty_input",
                    "error_message": "Email request cannot be empty"
                }
            
            # Truncate if too long
            if len(email_request) > config.max_input_length:
                logger.warning(f"Email request too long ({len(email_request)} chars), truncating")
                email_request = email_request[:config.max_input_length]
            
            # Sanitize user context to prevent prompt injection
            if user_context:
                user_context = self._sanitize_user_context(user_context)
            
            # Check cache first
            cache_key = self._generate_cache_key(email_request, user_context)
            
            if config.cache_enabled:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result:
                    logger.info("Using cached email generation")
                    cached_result['from_cache'] = True
                    cached_result['cache_timestamp'] = self._get_timestamp()
                    return cached_result
            
            # Build context-aware prompt using SystemPrompts helper
            system_prompt = self._build_system_prompt(user_context)
            user_message = f"Email request: {email_request}"
            
            # Generate using OpenAI with cost check
            llm_response = self.model_manager.generate_completion_with_cost_check(
                system_prompt=system_prompt,
                user_message=user_message,
                model_type="primary",  # Use best model for professional emails
                temperature=0.3  # Slightly higher than comments for natural tone
            )
            
            if not llm_response["success"]:
                return {
                    "success": False,
                    "error": llm_response.get("error", "generation_failed"),
                    "error_message": llm_response.get("error_message", "Failed to generate email"),
                    "email_request": email_request
                }
            
            # Process the email
            generated_email = llm_response["content"].strip()
            
            # Validate email is not empty
            if not generated_email:
                logger.error("LLM returned empty email")
                return {
                    "success": False,
                    "error": "empty_response",
                    "error_message": "Generated email is empty",
                    "email_request": email_request
                }
            
            # Extract email components
            email_parts = self._parse_email_components(generated_email)
            
            # Validate email structure
            validation_result = self._validate_email_structure(email_parts)
            
            result = {
                "success": True,
                "email_request": email_request,
                "generated_email": generated_email,
                "email_components": email_parts,
                "requires_approval": True,  # Always require approval for emails
                "validation": validation_result,
                "word_count": len(generated_email.split()),
                "processing_metadata": {
                    "model_used": llm_response.get("model_used"),
                    "tokens_used": llm_response.get("usage", {}).get("total_tokens"),
                    "temperature": 0.3,
                    "cached": False,
                    "processing_time": llm_response.get("metadata", {}).get("processing_time_seconds")
                },
                "from_cache": False
            }
            
            # Cache if validation passed
            if config.cache_enabled and validation_result.get("valid", False):
                try:
                    self.cache_manager.set(
                        cache_key, 
                        result, 
                        ttl_minutes=config.cache_ttl_email_minutes
                    )
                    logger.debug("Cached generated email")
                except Exception as e:
                    logger.warning(f"Failed to cache email: {e}")
            
            logger.info("Generated professional email successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "generation_failed",
                "error_message": str(e),
                "email_request": email_request
            }
    
    def _build_system_prompt(self, user_context: Optional[Dict[str, Any]]) -> str:
        """
        Build context-aware email prompt using SystemPrompts helper
        
        Args:
            user_context: User context (name, manager, department)
            
        Returns:
            System prompt with optional context
        """
        if not user_context:
            return self.prompts.EMAIL_GENERATOR
        
        # Use SystemPrompts helper method for context-aware prompts
        return SystemPrompts.build_email_prompt_with_context(
            user_name=user_context.get("user_name"),
            manager_name=user_context.get("manager_name"),
            department=user_context.get("department")
        )
    
    def _sanitize_user_context(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize user context to prevent prompt injection
        
        Args:
            user_context: Raw user context
            
        Returns:
            Sanitized user context
        """
        sanitized = {}
        
        # Define safe fields and their max lengths
        safe_fields = {
            "user_name": 100,
            "manager_name": 100,
            "department": 100,
            "user_id": 50,
            "role": 50
        }
        
        for field, max_length in safe_fields.items():
            if field in user_context:
                value = str(user_context[field])
                
                # Remove potentially dangerous characters
                value = re.sub(r'[<>{}[\]\\]', '', value)
                
                # Remove newlines and control characters
                value = re.sub(r'[\n\r\t]', ' ', value)
                
                # Truncate to max length
                value = value[:max_length]
                
                # Only include if not empty after sanitization
                if value.strip():
                    sanitized[field] = value.strip()
        
        # Copy non-string fields as-is (user_id, etc.)
        for key, value in user_context.items():
            if key not in safe_fields and not isinstance(value, str):
                sanitized[key] = value
        
        return sanitized
    
    def _generate_cache_key(
        self, 
        email_request: str, 
        user_context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate deterministic cache key for email request
        
        Args:
            email_request: Email request text
            user_context: User context (affects prompt)
            
        Returns:
            Cache key string
        """
        # Normalize request
        normalized = email_request.lower().strip()[:200]
        
        # Include relevant context in key (names affect email generation)
        context_key = ""
        if user_context:
            names = [
                user_context.get("user_name", ""),
                user_context.get("manager_name", "")
            ]
            context_key = ":".join(filter(None, names))
        
        # Create hash of request + context
        content = f"{normalized}:{context_key}"
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
        
        return f"email:{content_hash}"
    
    def _parse_email_components(self, email: str) -> Dict[str, str]:
        """
        Parse email into components (subject, body, etc.)
        
        Args:
            email: Full email text
            
        Returns:
            Dictionary with parsed components
        """
        components = {
            "subject": None,
            "greeting": None,
            "closing": None,
            "full_email": email
        }
        
        lines = email.split('\n')
        
        # Extract subject line
        for line in lines:
            if line.strip().lower().startswith('subject:'):
                components['subject'] = line.replace('Subject:', '').replace('subject:', '').strip()
                break
        
        # Extract greeting
        greeting_patterns = ['dear', 'hello', 'hi', 'good morning', 'good afternoon']
        for line in lines:
            line_lower = line.lower()
            if any(greeting in line_lower for greeting in greeting_patterns):
                components['greeting'] = line.strip()
                break
        
        # Extract closing
        closing_patterns = ['regards', 'sincerely', 'best', 'thank you', 'thanks']
        for line in reversed(lines):
            line_lower = line.lower()
            if any(closing in line_lower for closing in closing_patterns):
                components['closing'] = line.strip()
                break
        
        return components
    
    def _validate_email_structure(self, email_parts: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate email has proper structure
        
        Args:
            email_parts: Parsed email components
            
        Returns:
            Validation result dict
        """
        issues = []
        warnings = []
        
        # Check for subject line
        if not email_parts.get("subject"):
            issues.append("Missing subject line")
        
        # Check for greeting
        if not email_parts.get("greeting"):
            warnings.append("No greeting found")
        
        # Check for closing
        if not email_parts.get("closing"):
            warnings.append("No closing found")
        
        # Check email length
        email_text = email_parts.get("full_email", "")
        word_count = len(email_text.split())
        
        if word_count < 10:
            issues.append("Email too short (less than 10 words)")
        elif word_count > 500:
            warnings.append("Email very long (over 500 words)")
        
        # Check for placeholders
        if "[" in email_text and "]" in email_text:
            # This is expected - email should have placeholders
            pass
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "has_subject": bool(email_parts.get("subject")),
            "has_greeting": bool(email_parts.get("greeting")),
            "has_closing": bool(email_parts.get("closing")),
            "word_count": word_count
        }
    
    def _get_timestamp(self) -> str:
        """Get current UTC timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()