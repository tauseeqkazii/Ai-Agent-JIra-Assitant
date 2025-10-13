"""
Response Validator Module
Validates AI-generated responses for quality and appropriateness
"""

import re
from typing import Dict, Any, List, Set
import logging

from ..core.config import config

logger = logging.getLogger(__name__)


class ResponseValidator:
    """
    Validates AI-generated responses for quality, professionalism, and security
    """
    
    def __init__(self):
        # Professional tone indicators
        self.professional_indicators = [
            'completed', 'implemented', 'resolved', 'pending', 'reviewing',
            'investigating', 'deployment', 'testing', 'development',
            'addressing', 'coordinating', 'optimizing', 'analyzing'
        ]
        
        # Unprofessional indicators to flag
        self.unprofessional_indicators = [
            'gonna', 'wanna', 'kinda', 'sorta', 'dunno', 'yeah', 'nope',
            'totally', 'awesome', 'cool', 'sucks', 'crap', 'dude', 'bro'
        ]
        
        # Compile sensitive information patterns
        self._compile_sensitive_patterns()
        
        logger.info("ResponseValidator initialized")
    
    def _compile_sensitive_patterns(self):
        """Compile regex patterns for sensitive information detection"""
        self.sensitive_patterns = {
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "credit_card": re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
            "password": re.compile(r'\bpassword[:\s]+\S+', re.IGNORECASE),
            # Email pattern - but we'll be smarter about it
            "personal_email": re.compile(r'\b[A-Za-z0-9._%+-]+@(?!company\.com|organization\.org)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        }
    
    def validate_response(
        self, 
        generated_content: str, 
        response_type: str
    ) -> Dict[str, Any]:
        """
        Validate AI-generated response for quality and appropriateness
        
        Args:
            generated_content: The AI-generated text
            response_type: Type of response (llm_rephrasing, llm_email, etc.)
            
        Returns:
            Validation results with scores and flags
        """
        try:
            validation_result = {
                "overall_score": 0.0,
                "professional_tone_score": 0.0,
                "length_appropriate": False,
                "has_sensitive_info": False,
                "flags": [],
                "recommendations": [],
                "approved_for_auto_send": False
            }
            
            # Check professional tone
            prof_score = self._check_professional_tone(generated_content)
            validation_result["professional_tone_score"] = prof_score
            
            # Check length appropriateness
            length_check = self._check_length(generated_content, response_type)
            validation_result["length_appropriate"] = length_check["appropriate"]
            if not length_check["appropriate"]:
                validation_result["flags"].append(length_check["issue"])
                validation_result["recommendations"].append(length_check["recommendation"])
            
            # Check for sensitive information
            sensitive_check = self._check_sensitive_info(generated_content)
            validation_result["has_sensitive_info"] = sensitive_check["found"]
            if sensitive_check["found"]:
                validation_result["flags"].extend(sensitive_check["types"])
                validation_result["recommendations"].append("Remove sensitive information before sending")
            
            # Check for completion markers (for comment rephrasing)
            if response_type == "llm_rephrasing":
                completion_check = self._check_completion_markers(generated_content)
                validation_result["has_completion_markers"] = completion_check["found"]
                if completion_check["found"]:
                    validation_result["flags"].append(
                        f"Contains completion markers: {', '.join(completion_check['markers'])}"
                    )
                    validation_result["recommendations"].append(
                        "Verify task is actually complete before marking as done"
                    )
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(validation_result)
            validation_result["overall_score"] = overall_score
            
            # Determine if approved for auto-send
            validation_result["approved_for_auto_send"] = (
                overall_score >= config.auto_approval_threshold and 
                not validation_result["has_sensitive_info"] and
                len(validation_result["flags"]) == 0
            )
            
            logger.info(
                f"Response validated - Score: {overall_score:.2f}, "
                f"Auto-approved: {validation_result['approved_for_auto_send']}"
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            return {
                "overall_score": 0.0,
                "error": "validation_failed",
                "approved_for_auto_send": False,
                "flags": ["Validation failed - manual review required"]
            }
    
    def _check_professional_tone(self, content: str) -> float:
        """
        Check professional tone of the content
        
        Args:
            content: Text to check
            
        Returns:
            Professionalism score (0.0 to 1.0)
        """
        if not content:
            return 0.0
        
        content_lower = content.lower()
        word_count = len(content.split())
        
        if word_count == 0:
            return 0.0
        
        # Count professional indicators
        prof_count = sum(1 for word in self.professional_indicators if word in content_lower)
        
        # Count unprofessional indicators (penalty)
        unprof_count = sum(1 for word in self.unprofessional_indicators if word in content_lower)
        
        # Calculate professional ratio (normalize by word count)
        prof_ratio = prof_count / max(word_count, 1)
        unprof_penalty = unprof_count * 0.2
        
        # Base score starts at 0.7
        base_score = 0.7
        prof_bonus = min(prof_ratio * 2, 0.3)  # Max 0.3 bonus
        
        score = base_score + prof_bonus - unprof_penalty
        return max(0.0, min(1.0, score))
    
    def _check_length(self, content: str, response_type: str) -> Dict[str, Any]:
        """
        Check if content length is appropriate for response type
        
        Args:
            content: Text to check
            response_type: Type of response
            
        Returns:
            Dictionary with appropriateness and feedback
        """
        word_count = len(content.split())
        char_count = len(content)
        
        if response_type == "llm_rephrasing":
            # Jira comments should be concise but informative
            if word_count < 3:
                return {
                    "appropriate": False,
                    "issue": "Comment too short (less than 3 words)",
                    "recommendation": "Add more detail about the task update"
                }
            elif word_count > 100:
                return {
                    "appropriate": False,
                    "issue": "Comment too long (over 100 words)",
                    "recommendation": "Make comment more concise for Jira"
                }
                
        elif response_type == "llm_email":
            # Emails can be longer but should be reasonable
            if word_count < 10:
                return {
                    "appropriate": False,
                    "issue": "Email too short (less than 10 words)",
                    "recommendation": "Add more context and proper email structure"
                }
            elif word_count > 300:
                return {
                    "appropriate": False,
                    "issue": "Email too long (over 300 words)",
                    "recommendation": "Make email more concise for better readability"
                }
        
        return {"appropriate": True}
    
    def _check_sensitive_info(self, content: str) -> Dict[str, Any]:
        """
        Check for potentially sensitive information
        
        Args:
            content: Text to check
            
        Returns:
            Dictionary with findings
        """
        found_types: Set[str] = set()
        
        # Check each pattern
        for info_type, pattern in self.sensitive_patterns.items():
            if pattern.search(content):
                if info_type == "ssn":
                    found_types.add("Potential SSN detected")
                elif info_type == "credit_card":
                    # Additional validation - check if it looks like a real credit card
                    # (simple Luhn algorithm check could go here)
                    found_types.add("Potential credit card number detected")
                elif info_type == "password":
                    found_types.add("Password information detected")
                elif info_type == "personal_email":
                    # Only flag non-business emails
                    found_types.add("Personal email address detected")
        
        return {
            "found": len(found_types) > 0,
            "types": list(found_types)
        }
    
    def _check_completion_markers(self, content: str) -> Dict[str, Any]:
        """
        Check for task completion markers in rephrased comments
        
        Args:
            content: Text to check
            
        Returns:
            Dictionary with found markers
        """
        completion_words = ['completed', 'finished', 'done', 'resolved', 'closed']
        content_lower = content.lower()
        
        found_markers = [word for word in completion_words if word in content_lower]
        
        return {
            "found": len(found_markers) > 0,
            "markers": found_markers
        }
    
    def _calculate_overall_score(self, validation_result: Dict[str, Any]) -> float:
        """
        Calculate overall validation score
        
        Args:
            validation_result: Current validation results
            
        Returns:
            Overall score (0.0 to 1.0)
        """
        base_score = validation_result["professional_tone_score"]
        
        # Length penalty
        if not validation_result["length_appropriate"]:
            base_score -= 0.2
        
        # Sensitive info penalty (major)
        if validation_result["has_sensitive_info"]:
            base_score -= 0.5
        
        # Flag penalties
        flag_penalty = len(validation_result["flags"]) * 0.1
        base_score -= flag_penalty
        
        return max(0.0, min(1.0, base_score))
    
    def quick_validate(self, content: str) -> bool:
        """
        Quick validation check (for performance)
        
        Args:
            content: Text to validate
            
        Returns:
            True if content passes basic checks
        """
        # Quick checks only
        if not content or len(content.strip()) < 3:
            return False
        
        # Check for obvious unprofessional words
        content_lower = content.lower()
        if any(word in content_lower for word in ['fuck', 'shit', 'damn', 'crap']):
            return False
        
        # Check for obvious sensitive info patterns
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', content):  # SSN
            return False
        
        return True