from typing import Dict, Any, Optional
import logging
from ..models.model_manager import ModelManager
from ..prompts.system_prompts import SystemPrompts

logger = logging.getLogger(__name__)

class EmailGenerator:
    """Generates professional emails based on user requests"""
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager or ModelManager()
        self.prompts = SystemPrompts()
    
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
            # Build context-aware prompt
            system_prompt = self._build_email_prompt(user_context)
            user_message = f"Email request: {email_request}"
            
            # Generate using OpenAI
            llm_response = self.model_manager.generate_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                model_type="primary",
                temperature=0.3  # Slightly higher for natural email tone
            )
            
            if not llm_response["success"]:
                return {
                    "success": False,
                    "error": llm_response.get("error", "generation_failed"),
                    "error_message": llm_response.get("error_message", "Failed to generate email")
                }
            
            # Process the email
            generated_email = llm_response["content"].strip()
            
            # Extract email components
            email_parts = self._parse_email_components(generated_email)
            
            result = {
                "success": True,
                "email_request": email_request,
                "generated_email": generated_email,
                "email_components": email_parts,
                "requires_approval": True,  # Always require approval for emails
                "processing_metadata": {
                    "model_used": llm_response["model_used"],
                    "tokens_used": llm_response["usage"]["total_tokens"],
                    "temperature": 0.3
                }
            }
            
            logger.info("Generated professional email successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}")
            return {
                "success": False,
                "error": "generation_failed",
                "error_message": str(e)
            }
    
    def _build_email_prompt(self, user_context: Optional[Dict[str, Any]]) -> str:
        """Build context-aware email prompt"""
        base_prompt = self.prompts.EMAIL_GENERATOR
        
        if not user_context:
            return base_prompt
        
        context_additions = []
        
        if user_context.get("user_name"):
            context_additions.append(f"User name: {user_context['user_name']}")
            
        if user_context.get("manager_name"):
            context_additions.append(f"Manager name: {user_context['manager_name']}")
            
        if user_context.get("department"):
            context_additions.append(f"Department: {user_context['department']}")
        
        if context_additions:
            context_info = "\nContext information:\n" + "\n".join(context_additions)
            return base_prompt + context_info
        
        return base_prompt
    
    def _parse_email_components(self, email: str) -> Dict[str, str]:
        """Parse email into components (subject, body, etc.)"""
        components = {}
        
        lines = email.split('\n')
        
        # Extract subject line
        for line in lines:
            if line.strip().startswith('Subject:'):
                components['subject'] = line.replace('Subject:', '').strip()
                break
        
        # Extract greeting
        for line in lines:
            if any(greeting in line.lower() for greeting in ['dear', 'hello', 'hi']):
                components['greeting'] = line.strip()
                break
        
        # Extract closing
        for line in reversed(lines):
            if any(closing in line.lower() for closing in ['regards', 'sincerely', 'best']):
                components['closing'] = line.strip()
                break
        
        components['full_email'] = email
        return components