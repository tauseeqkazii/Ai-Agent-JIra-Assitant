"""
Main entry point for AI Engine
This is what the backend team will import and use
"""

from typing import Dict, Any
import logging
import time
from .core.pipeline import AIProcessingPipeline
from .core.config import config
from .utils.monitoring import production_monitor
from .utils.error_handler import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.is_production else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class JiraAIAssistant:
    """
    Main AI Assistant class - this is the interface for backend team
    """
    
    def __init__(self):
        """Initialize the AI Assistant"""
        try:
            self.pipeline = AIProcessingPipeline()
            self.initialized = True
            logger.info("Jira AI Assistant initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Assistant: {str(e)}")
            self.initialized = False
            raise
    
    @error_handler.with_error_handling("main_processing", fallback_response={
        "success": False,
        "error": "processing_unavailable",
        "error_message": "AI processing temporarily unavailable",
        "backend_action": "show_error_message"
    })
    def process_user_message(self, user_input: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method for processing user messages
        
        Args:
            user_input: Raw user message
            user_context: User information and context
            
        Returns:
            Processing result with actions for backend
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "not_initialized",
                "error_message": "AI Assistant not properly initialized"
            }
        
        # Validate inputs
        if not user_input or not user_input.strip():
            return {
                "success": False,
                "error": "empty_input",
                "error_message": "Please provide a message",
                "backend_action": "request_input"
            }
        
        if not user_context or not user_context.get("user_id"):
            return {
                "success": False,
                "error": "missing_context",
                "error_message": "User context required",
                "backend_action": "request_authentication"
            }
        
        # Process the request
        logger.info(f"Processing request from user {user_context.get('user_id')}: {user_input[:50]}...")
        
        result = self.pipeline.process_user_request(user_input, user_context)
        
        # Add processing metadata
        result["processing_metadata"] = {
            **result.get("processing_metadata", {}),
            "ai_engine_version": "1.0.0",
            "config_environment": config.environment,
            "request_id": f"{user_context.get('user_id')}_{int(time.time())}"
        }
        
        logger.info(f"Request processed successfully: {result.get('route_type', 'unknown')}")
        return result
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get AI system health status"""
        return production_monitor.get_health_status()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance and monitoring metrics"""
        return production_monitor.get_performance_metrics()
    
    def get_cost_analysis(self) -> Dict[str, Any]:
        """Get cost analysis and optimization suggestions"""
        return production_monitor.get_cost_analysis()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration"""
        try:
            issues = []
            warnings = []
            
            # Check OpenAI configuration
            if not config.openai_api_key:
                issues.append("OpenAI API key not configured")
            elif not config.openai_api_key.startswith('sk-'):
                issues.append("Invalid OpenAI API key format")
            
            # Check model availability
            if config.openai_primary_model not in ["gpt-4-turbo-preview", "gpt-4"]:
                warnings.append("Primary model may not be optimal for production")
            
            # Check thresholds
            if config.confidence_threshold < 0.7:
                warnings.append("Confidence threshold is low - may affect quality")
            
            if config.quality_threshold < 0.6:
                warnings.append("Quality threshold is low - may need manual review")
            
            # Check production settings
            if config.is_production and config.debug_mode:
                warnings.append("Debug mode enabled in production environment")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "environment": config.environment,
                "cache_enabled": config.cache_enabled,
                "monitoring_enabled": config.metrics_collection_enabled
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Configuration validation failed: {str(e)}"
            }

# Create global instance for backend to import
ai_assistant = JiraAIAssistant()

# Convenience functions for backend team
def process_message(user_input: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for processing messages"""
    return ai_assistant.process_user_message(user_input, user_context)

def get_health() -> Dict[str, Any]:
    """Convenience function for health checks"""
    return ai_assistant.get_health_status()

def get_metrics() -> Dict[str, Any]:
    """Convenience function for metrics"""
    return ai_assistant.get_performance_metrics()