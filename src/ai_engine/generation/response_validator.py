import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ResponseValidator:
    """Validates AI-generated responses for quality and appropriateness"""
    
    def __init__(self):
        # Professional tone indicators
        self.professional_indicators = [
            'completed', 'implemented', 'resolved', 'pending', 'reviewing',
            'investigating', 'deployment', 'testing', 'development'
        ]
        
        # Unprofessional indicators to flag
        self.unprofessional_indicators = [
            'gonna', 'wanna', 'kinda', 'sorta', 'dunno', 'yeah', 'nope',
            'totally', 'awesome', 'cool', 'sucks', 'crap'
        ]
        
        # Sensitive information patterns to flag
        self.sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
            r'\bpassword[:\s]+\S+',  # Password
        ]
    
    def validate_response(self, generated_content: str, response_type: str) -> Dict[str, Any]:
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
                    validation_result["flags"].append("Contains completion markers - verify task is actually complete")
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(validation_result)
            validation_result["overall_score"] = overall_score
            
            # Determine if approved for auto-send
            validation_result["approved_for_auto_send"] = (
                overall_score >= 0.8 and 
                not validation_result["has_sensitive_info"] and
                len(validation_result["flags"]) == 0
            )
            
            logger.info(f"Response validated - Score: {overall_score:.2f}, Auto-approved: {validation_result['approved_for_auto_send']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                "overall_score": 0.0,
                "error": "validation_failed",
                "approved_for_auto_send": False,
                "flags": ["Validation failed - manual review required"]
            }
    
    def _check_professional_tone(self, content: str) -> float:
        """Check professional tone of the content"""
        content_lower = content.lower()
        
        # Count professional indicators
        prof_count = sum(1 for word in self.professional_indicators if word in content_lower)
        
        # Count unprofessional indicators (penalty)
        unprof_count = sum(1 for word in self.unprofessional_indicators if word in content_lower)
        
        # Basic score calculation
        word_count = len(content.split())
        if word_count == 0:
            return 0.0
        
        # Professional ratio
        prof_ratio = prof_count / max(word_count, 1)
        unprof_penalty = unprof_count * 0.2
        
        # Base score starts at 0.7, increases with professional words, decreases with unprofessional
        base_score = 0.7
        prof_bonus = min(prof_ratio * 2, 0.3)  # Max 0.3 bonus
        
        score = base_score + prof_bonus - unprof_penalty
        return max(0.0, min(1.0, score))
    
    def _check_length(self, content: str, response_type: str) -> Dict[str, Any]:
        """Check if content length is appropriate for response type"""
        word_count = len(content.split())
        char_count = len(content)
        
        if response_type == "llm_rephrasing":
            # Jira comments should be concise but informative
            if word_count < 3:
                return {
                    "appropriate": False,
                    "issue": "Comment too short",
                    "recommendation": "Add more detail about the task update"
                }
            elif word_count > 100:
                return {
                    "appropriate": False,
                    "issue": "Comment too long",
                    "recommendation": "Make comment more concise for Jira"
                }
                
        elif response_type == "llm_email":
            # Emails can be longer but should be reasonable
            if word_count < 10:
                return {
                    "appropriate": False,
                    "issue": "Email too short",
                    "recommendation": "Add more context and proper email structure"
                }
            elif word_count > 300:
                return {
                    "appropriate": False,
                    "issue": "Email too long",
                    "recommendation": "Make email more concise for better readability"
                }
        
        return {"appropriate": True}
    
    def _check_sensitive_info(self, content: str) -> Dict[str, Any]:
        """Check for potentially sensitive information"""
        found_types = []
        
        for pattern in self.sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                if 'SSN' not in str(found_types) and r'\d{3}-\d{2}-\d{4}' in pattern:
                    found_types.append("Potential SSN detected")
                elif 'email' not in str(found_types).lower() and '@' in pattern:
                    found_types.append("Email address detected")
                elif 'credit card' not in str(found_types).lower() and r'\d{4}' in pattern:
                    found_types.append("Potential credit card number detected")
                elif 'password' not in str(found_types).lower() and 'password' in pattern:
                    found_types.append("Password information detected")
        
        return {
            "found": len(found_types) > 0,
            "types": found_types
        }
    
    def _check_completion_markers(self, content: str) -> Dict[str, Any]:
        """Check for task completion markers in rephrased comments"""
        completion_words = ['completed', 'finished', 'done', 'resolved', 'closed']
        content_lower = content.lower()
        
        found_markers = [word for word in completion_words if word in content_lower]
        
        return {
            "found": len(found_markers) > 0,
            "markers": found_markers
        }
    
    def _calculate_overall_score(self, validation_result: Dict[str, Any]) -> float:
        """Calculate overall validation score"""
        base_score = validation_result["professional_tone_score"]
        
        # Length penalty
        if not validation_result["length_appropriate"]:
            base_score -= 0.2
        
        # Sensitive info penalty
        if validation_result["has_sensitive_info"]:
            base_score -= 0.5
        
        # Flag penalties
        flag_penalty = len(validation_result["flags"]) * 0.1
        base_score -= flag_penalty
        
        return max(0.0, min(1.0, base_score))