"""
Model Manager Module
Manages OpenAI/Azure OpenAI API calls with unified interface
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from openai import OpenAI, AzureOpenAI
import openai

from ..core.config import config
from ..utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages OpenAI/Azure OpenAI API calls with error handling and fallbacks
    """
    
    def __init__(self, metrics: Optional[MetricsCollector] = None):
        """
        Initialize model manager with appropriate client (OpenAI or Azure)
        
        Args:
            metrics: Optional metrics collector instance
        """
        self.metrics = metrics or MetricsCollector()
        
        # Initialize the appropriate client based on provider
        if config.is_azure:
            logger.info("Initializing Azure OpenAI client")
            self.client = AzureOpenAI(
                api_key=config.openai_api_key,
                api_version=config.azure_api_version,
                azure_endpoint=config.azure_api_base
            )
            logger.info(f"Azure OpenAI configured with endpoint: {config.azure_api_base}")
            logger.info(f"Available models: {', '.join(config.model_config_map.values())}")
        else:
            logger.info("Initializing OpenAI client")
            self.client = OpenAI(api_key=config.openai_api_key)
        
        # Model configurations from config
        self.models = config.model_config_map
        self.token_limits = config.token_limits
        
        logger.info(
            f"ModelManager initialized with provider: {config.api_provider}, "
            f"primary model: {self.models['primary']}"
        )
    
    def generate_completion(
        self, 
        system_prompt: str, 
        user_message: str,
        model_type: str = "primary",
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate completion using OpenAI/Azure OpenAI API
        
        Args:
            system_prompt: System instructions
            user_message: User input to process
            model_type: Which model to use (primary/fast/classification)
            temperature: Creativity level (0.0-1.0)
            max_tokens: Max response length
        
        Returns:
            Dict with response and metadata
        """
        try:
            # Validate inputs
            if not system_prompt or not user_message:
                return {
                    "success": False,
                    "error": "invalid_input",
                    "error_message": "System prompt and user message are required"
                }
            
            # Get model configuration
            model_name = self.models.get(model_type, self.models["primary"])
            if max_tokens is None:
                max_tokens = self.token_limits.get(model_name, 1000)
            
            # Record API call start time
            start_time = datetime.utcnow()
            
            # Prepare API call parameters
            api_params = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.9,
                "timeout": config.openai_timeout_seconds
            }
            
            # Add model parameter differently based on provider
            if config.is_azure:
                # For Azure, use deployment name (not model name)
                api_params["model"] = model_name
                logger.debug(f"Using Azure deployment: {model_name}")
            else:
                # For OpenAI, use model name
                api_params["model"] = model_name
                logger.debug(f"Using OpenAI model: {model_name}")
            
            # Make API call
            response = self.client.chat.completions.create(**api_params)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Extract response data
            result = {
                "success": True,
                "content": response.choices[0].message.content,
                "model_used": model_name,
                "api_provider": config.api_provider,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "metadata": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "processing_time_seconds": round(processing_time, 3)
                }
            }
            
            # Record metrics with cost tracking
            try:
                self.metrics.record_api_call(
                    model=model_name,
                    tokens_used=response.usage.total_tokens,
                    success=True,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens
                )
            except Exception as e:
                logger.warning(f"Failed to record API metrics: {e}")
            
            logger.info(
                f"API call successful - {config.api_provider}/{model_name} - "
                f"{response.usage.total_tokens} tokens - {processing_time:.2f}s"
            )
            
            return result
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit hit: {str(e)}")
            return self._handle_rate_limit_error(system_prompt, user_message, model_type)
            
        except openai.APIError as e:
            logger.error(f"API error: {str(e)}")
            
            # Record failed API call
            try:
                self.metrics.record_api_call(
                    model=self.models.get(model_type, "unknown"),
                    tokens_used=0,
                    success=False
                )
            except:
                pass
            
            return {
                "success": False,
                "error": "api_error",
                "error_message": str(e),
                "fallback_available": True
            }
        
        except openai.APITimeoutError as e:
            logger.error(f"API timeout: {str(e)}")
            
            try:
                self.metrics.record_api_call(
                    model=self.models.get(model_type, "unknown"),
                    tokens_used=0,
                    success=False
                )
            except:
                pass
            
            return {
                "success": False,
                "error": "timeout",
                "error_message": f"Request timed out after {config.openai_timeout_seconds}s",
                "fallback_available": True
            }
        
        except openai.AuthenticationError as e:
            logger.error(f"Authentication error: {str(e)}")
            return {
                "success": False,
                "error": "authentication_error",
                "error_message": "Invalid API key or authentication failed",
                "fallback_available": False
            }
            
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid input or configuration: {str(e)}")
            return {
                "success": False,
                "error": "invalid_input",
                "error_message": str(e),
                "fallback_available": False
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in API call: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "unexpected_error",
                "error_message": str(e),
                "fallback_available": False
            }
    
    def _handle_rate_limit_error(
        self, 
        system_prompt: str, 
        user_message: str, 
        model_type: str
    ) -> Dict:
        """
        Handle rate limit by trying a different model or queuing
        
        Args:
            system_prompt: System instructions
            user_message: User input
            model_type: Originally requested model type
            
        Returns:
            Response dict (either from fallback or error)
        """
        if model_type == "primary":
            # Fallback to faster model
            logger.info("Rate limit on primary model, trying fast model")
            
            # Recursive call with fast model (only retries once)
            return self.generate_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                model_type="fast",
                temperature=0.3
            )
        
        # Already tried fallback or using non-primary model
        logger.error("Rate limit reached on all models")
        
        return {
            "success": False,
            "error": "rate_limit",
            "error_message": "All models are rate limited. Please try again in a few minutes.",
            "retry_after_seconds": 60,
            "fallback_available": False
        }
    
    def check_daily_cost_limit(self) -> Dict[str, Any]:
        """
        Check if daily cost limit has been reached
        
        Returns:
            Dict with cost status and whether limit is reached
        """
        try:
            daily_cost = self.metrics.get_daily_cost()
            max_cost = config.max_daily_cost_usd
            alert_threshold = config.alert_at_cost_usd
            
            limit_reached = daily_cost >= max_cost
            alert_needed = daily_cost >= alert_threshold
            
            return {
                "daily_cost": daily_cost,
                "max_cost": max_cost,
                "limit_reached": limit_reached,
                "alert_needed": alert_needed,
                "percentage_used": round((daily_cost / max_cost) * 100, 1) if max_cost > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error checking cost limit: {e}")
            return {
                "daily_cost": 0.0,
                "limit_reached": False,
                "error": str(e)
            }
    
    def generate_completion_with_cost_check(
        self,
        system_prompt: str,
        user_message: str,
        model_type: str = "primary",
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate completion with automatic cost limit checking
        
        Args:
            Same as generate_completion
            
        Returns:
            Response dict (with cost limit check)
        """
        # Check cost limit before making API call
        cost_status = self.check_daily_cost_limit()
        
        if cost_status["limit_reached"]:
            logger.error(
                f"Daily cost limit reached: ${cost_status['daily_cost']:.2f} / "
                f"${cost_status['max_cost']:.2f}"
            )
            return {
                "success": False,
                "error": "cost_limit_reached",
                "error_message": f"Daily cost limit of ${cost_status['max_cost']:.2f} reached",
                "current_cost": cost_status["daily_cost"],
                "fallback_available": False
            }
        
        # Alert if approaching limit
        if cost_status["alert_needed"]:
            logger.warning(
                f"Approaching cost limit: ${cost_status['daily_cost']:.2f} / "
                f"${cost_status['max_cost']:.2f} ({cost_status['percentage_used']}%)"
            )
        
        # Proceed with normal generation
        return self.generate_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            model_type=model_type,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def get_model_stats(self) -> Dict[str, Any]:
        """
        Get model usage statistics
        
        Returns:
            Dict with model usage stats
        """
        try:
            stats = self.metrics.get_stats()
            return {
                "total_api_calls": stats.get("total_api_calls", 0),
                "successful_calls": stats.get("successful_api_calls", 0),
                "total_tokens": stats.get("total_tokens", 0),
                "total_cost_usd": stats.get("total_cost_usd", 0.0),
                "average_cost_per_call": stats.get("average_cost_per_call", 0.0)
            }
        except Exception as e:
            logger.error(f"Error getting model stats: {e}")
            return {"error": str(e)}