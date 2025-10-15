"""
Main Entry Point for AI Engine
This is the interface for the backend team to use
"""

import time
import logging
from typing import Dict, Any, Optional

from .core.pipeline import AIProcessingPipeline
from .core.config import config
from .utils.monitoring import production_monitor
from .utils.error_handler import error_handler
import os
from dotenv import load_dotenv

# Load .env file so all os.getenv calls see the values
load_dotenv()  # By default, looks for .env in the current working directory

# Configure logging based on environment
logging.basicConfig(
    level=logging.DEBUG if config.debug_mode else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

import openai
import os

# Azure OpenAI setup
openai_api_base = os.getenv("OPENAI_API_BASE_URL")
if openai_api_base is None:
    raise ValueError("OPENAI_API_BASE_URL environment variable not set")

openai.api_type = "azure"
openai.api_base = openai_api_base
openai.api_version = "2023-07-01-preview"  # your Azure version
openai.api_key = os.getenv("OPENAI_API_KEY")


class JiraAIAssistant:
    """
    Main AI Assistant class - clean interface for backend team
    
    Usage:
        from src.ai_engine.main import ai_assistant
        
        result = ai_assistant.process_user_message(
            user_input="I tested the API",
            user_context={"user_id": "123", "user_name": "John"}
        )
    """
    
    def __init__(self):
        """Initialize the AI Assistant with all dependencies"""
        try:
            self.pipeline = AIProcessingPipeline()
            self.initialized = True
            
            logger.info(
                f"Jira AI Assistant initialized successfully "
                f"(Environment: {config.environment})"
            )
            
            # Log configuration summary
            if config.debug_mode:
                logger.debug(f"Config: {self._get_config_summary()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Assistant: {str(e)}", exc_info=True)
            self.initialized = False
            raise
    
    @error_handler.with_error_handling(
        "main_processing",
        fallback_response={
            "success": False,
            "error": "processing_unavailable",
            "error_message": "AI processing temporarily unavailable",
            "backend_action": "show_error_message"
        }
    )
    def process_user_message(
        self, 
        user_input: str, 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main method for processing user messages
        
        Args:
            user_input: Raw user message
            user_context: User information and context
                Required fields: user_id
                Optional fields: user_name, manager_name, role, department, etc.
        
        Returns:
            Processing result with actions for backend
            
        Example:
            result = assistant.process_user_message(
                user_input="done with testing",
                user_context={
                    "user_id": "user123",
                    "user_name": "John Doe",
                    "role": "Senior Engineer"
                }
            )
            
            if result["success"]:
                action = result["backend_action"]
                # Handle action: mark_task_complete, show_comment_for_approval, etc.
        """
        validation_result = self._validate_user_permissions(user_context, user_input)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": "insufficient_permissions",
                "error_message": validation_result["message"],
                "backend_action": "request_authentication"
            }
        if not self.initialized:
            return {
                "success": False,
                "error": "not_initialized",
                "error_message": "AI Assistant not properly initialized",
                "backend_action": "show_error_message"
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
                "error_message": "User context with user_id is required",
                "backend_action": "request_authentication"
            }
        
        # Check daily cost limit before processing
        cost_status = self.pipeline.model_manager.check_daily_cost_limit()
        
        if cost_status.get("limit_reached"):
            logger.error(
                f"Daily cost limit reached: ${cost_status['daily_cost']:.2f} / "
                f"${cost_status['max_cost']:.2f}"
            )
            return {
                "success": False,
                "error": "cost_limit_reached",
                "error_message": f"Daily AI processing limit reached. Please try again tomorrow.",
                "current_cost": cost_status["daily_cost"],
                "max_cost": cost_status["max_cost"],
                "backend_action": "show_cost_limit_message"
            }
        
        # Alert if approaching limit
        if cost_status.get("alert_needed"):
            logger.warning(
                f"Approaching cost limit: ${cost_status['daily_cost']:.2f} / "
                f"${cost_status['max_cost']:.2f} ({cost_status['percentage_used']}%)"
            )
        
        # Process the request
        logger.info(
            f"Processing request from user {user_context.get('user_id')}: "
            f"{user_input[:50]}{'...' if len(user_input) > 50 else ''}"
        )
        
        result = self.pipeline.process_user_request(user_input, user_context)
        
        # Add AI engine metadata
        result["ai_engine_metadata"] = {
            "version": "2.0",
            "environment": config.environment,
            "request_id": f"{user_context.get('user_id')}_{int(time.time())}",
            "cost_status": {
                "daily_cost": cost_status["daily_cost"],
                "percentage_used": cost_status["percentage_used"]
            }
        }
        
        logger.info(
            f"Request processed: {result.get('route_type', 'unknown')} "
            f"(Success: {result.get('success', False)})"
        )
        
        return result
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get AI system health status
        
        Returns:
            Health status with component checks
            
        Example:
            health = assistant.get_health_status()
            if not health["healthy"]:
                # Alert ops team
        """
        return production_monitor.get_health_status()
    
    def _validate_user_permissions(self, user_context: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """
        Validate user has necessary permissions for the request
        
        Args:
            user_context: User information
            user_input: User's request
            
        Returns:
            Validation result
        """
        # Check for basic user info
        required_fields = ["user_id"]
        missing_fields = [f for f in required_fields if not user_context.get(f)]
        
        if missing_fields:
            return {
                "valid": False,
                "message": f"Missing required user information: {', '.join(missing_fields)}"
            }
        
        # Check if email request requires email-specific permissions
        if "email" in user_input.lower():
            if not user_context.get("user_name") or not user_context.get("manager_name"):
                return {
                    "valid": False,
                    "message": "Email generation requires your name and manager's name in your profile. Please update your profile settings."
                }
        
        # Check if Jira request requires Jira credentials
        # (Backend should populate this)
        jira_keywords = ["task", "jira", "bug", "ticket", "issue"]
        if any(kw in user_input.lower() for kw in jira_keywords):
            if not user_context.get("jira_connected"):
                return {
                    "valid": False,
                    "message": "Jira integration required. Please connect your Jira account in settings."
                }
        
        return {"valid": True}
    
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance and monitoring metrics
        
        Returns:
            Comprehensive metrics for monitoring dashboard
            
        Example:
            metrics = assistant.get_performance_metrics()
            print(f"Cache hit rate: {metrics['performance']['cache_hit_rate']}")
            print(f"Total cost: ${metrics['requests']['total_cost_usd']}")
        """
        return production_monitor.get_performance_metrics()
    
    def get_cost_analysis(self) -> Dict[str, Any]:
        """
        Get cost analysis and optimization suggestions
        
        Returns:
            Cost breakdown and optimization recommendations
            
        Example:
            costs = assistant.get_cost_analysis()
            print(f"Daily cost: ${costs['total_cost_estimate']}")
            for suggestion in costs['optimization_suggestions']:
                print(f"- {suggestion}")
        """
        return production_monitor.get_cost_analysis()
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics
        
        Returns:
            Pipeline performance stats
        """
        return self.pipeline.get_pipeline_stats()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate current configuration
        
        Returns:
            Validation results with issues and warnings
            
        Example:
            validation = assistant.validate_configuration()
            if not validation["valid"]:
                for issue in validation["issues"]:
                    print(f"ERROR: {issue}")
            for warning in validation["warnings"]:
                print(f"WARNING: {warning}")
        """
        try:
            issues = []
            warnings = []
            
            # Check OpenAI configuration
            if not config.openai_api_key:
                issues.append("OpenAI API key not configured")
            elif not config.openai_api_key.startswith('sk-'):
                issues.append("Invalid OpenAI API key format")
            
            # Check model configuration
            if config.openai_primary_model not in ["gpt-4o", "gpt-4", "gpt-4-turbo-preview"]:
                warnings.append(f"Unusual primary model: {config.openai_primary_model}")
            
            # Check thresholds
            if config.confidence_threshold < 0.7:
                warnings.append("Confidence threshold is low - may affect accuracy")
            
            if config.quality_threshold < 0.6:
                warnings.append("Quality threshold is low - may need more manual reviews")
            
            # Check production settings
            if config.is_production and config.debug_mode:
                warnings.append("Debug mode enabled in production environment")
            
            # Check cost limits
            if config.max_daily_cost_usd <= 0:
                warnings.append("No daily cost limit set")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "environment": config.environment,
                "cache_enabled": config.cache_enabled,
                "monitoring_enabled": config.metrics_collection_enabled,
                "primary_model": config.openai_primary_model,
                "max_daily_cost": config.max_daily_cost_usd
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Configuration validation failed: {str(e)}"
            }
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging"""
        return {
            "environment": config.environment,
            "primary_model": config.openai_primary_model,
            "cache_enabled": config.cache_enabled,
            "max_daily_cost": config.max_daily_cost_usd,
            "debug_mode": config.debug_mode
        }


# ============================================================================
# Global Instance - Backend team imports this
# ============================================================================

ai_assistant = JiraAIAssistant()


# ============================================================================
# Convenience Functions for Backend Team
# ============================================================================

def process_message(user_input: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for processing messages
    
    Args:
        user_input: User's message
        user_context: User information (must include user_id)
    
    Returns:
        Processing result
    
    Example:
        from src.ai_engine.main import process_message
        
        result = process_message(
            "I tested the API",
            {"user_id": "123", "user_name": "John"}
        )
    """
    return ai_assistant.process_user_message(user_input, user_context)


def get_health() -> Dict[str, Any]:
    """
    Convenience function for health checks
    
    Example:
        from src.ai_engine.main import get_health
        
        health = get_health()
        if not health["healthy"]:
            # Alert ops
    """
    return ai_assistant.get_health_status()


def get_metrics() -> Dict[str, Any]:
    """
    Convenience function for metrics
    
    Example:
        from src.ai_engine.main import get_metrics
        
        metrics = get_metrics()
        print(f"Total cost: ${metrics['requests']['total_cost_usd']}")
    """
    return ai_assistant.get_performance_metrics()


def get_costs() -> Dict[str, Any]:
    """
    Convenience function for cost analysis
    
    Example:
        from src.ai_engine.main import get_costs
        
        costs = get_costs()
        print(f"Daily cost: ${costs['total_cost_estimate']}")
    """
    return ai_assistant.get_cost_analysis()