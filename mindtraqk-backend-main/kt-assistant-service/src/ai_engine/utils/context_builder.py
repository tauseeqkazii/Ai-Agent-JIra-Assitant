"""
Context Builder Utility
Converts backend/DB user data to AI engine context format
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build AI engine context from backend user data"""
    
    @staticmethod
    def build_from_jira_user(
        user_db_data: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build AI context from Jira user MongoDB document
        
        Args:
            user_db_data: MongoDB user document
            additional_context: Optional extra context (current_task, etc.)
            
        Returns:
            Formatted context for AI engine
        """
        try:
            profile = user_db_data.get("profileData", {})
            
            # Extract user information
            context = {
                # Required fields
                "user_id": user_db_data.get("userId"),
                "jira_account_id": profile.get("accountId"),
                
                # User profile
                "user_name": profile.get("displayName"),
                "email_address": profile.get("emailAddress"),
                "timezone": profile.get("timeZone"),
                
                # Jira connection status
                "jira_connected": user_db_data.get("platform") == "jira",
                "jira_access_token": user_db_data.get("accessToken"),
                "jira_token_expires": user_db_data.get("expiresAt"),
                
                # Check if token is still valid
                "jira_token_valid": ContextBuilder._is_token_valid(
                    user_db_data.get("expiresAt")
                ),
                
                # Platform info
                "platform": user_db_data.get("platform", "jira"),
                "account_active": profile.get("active", True),
            }
            
            # Add additional context if provided
            if additional_context:
                context.update(additional_context)
            
            # Validate required fields
            if not context["user_id"]:
                logger.error("Missing user_id in user data")
                raise ValueError("user_id is required")
            
            if not context["jira_connected"]:
                logger.warning(f"User {context['user_id']} does not have Jira connected")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to build context from user data: {e}")
            raise
    
    @staticmethod
    def _is_token_valid(expires_at: Optional[str]) -> bool:
        """Check if Jira token is still valid"""
        if not expires_at:
            return False
        
        try:
            # Parse expiry date
            if isinstance(expires_at, dict) and "$date" in expires_at:
                expires_at = expires_at["$date"]
            
            expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            return datetime.now(expiry_date.tzinfo) < expiry_date
            
        except Exception as e:
            logger.warning(f"Failed to parse token expiry: {e}")
            return False
    
    @staticmethod
    def extract_manager_info(user_db_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract manager name from user data (if your DB stores it)
        You'll need to add this field to your user schema
        """
        # Example: return user_db_data.get("managerName")
        return None  # Implement based on your schema
    
    @staticmethod
    def validate_context(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate context has all required fields
        
        Returns:
            Dict with validation status and missing fields
        """
        required_fields = ["user_id", "jira_connected"]
        recommended_fields = ["user_name", "email_address", "jira_account_id"]
        
        missing_required = [f for f in required_fields if not context.get(f)]
        missing_recommended = [f for f in recommended_fields if not context.get(f)]
        
        return {
            "valid": len(missing_required) == 0,
            "missing_required": missing_required,
            "missing_recommended": missing_recommended,
            "warnings": [
                f"Missing recommended field: {f}" 
                for f in missing_recommended
            ]
        }