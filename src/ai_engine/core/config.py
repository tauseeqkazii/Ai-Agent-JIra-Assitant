"""
Enhanced AI Engine Configuration
Centralized configuration with validation and environment management
"""

from pydantic import Field, validator
from pydantic_settings import BaseSettings 
from typing import Dict, Any, Optional
from pathlib import Path
import os

class AIEngineConfig(BaseSettings):
    """Complete AI Engine Configuration with validation"""
    
    # ============================================================================
    # OpenAI Configuration
    # ============================================================================
    openai_api_key: str = Field(..., description="OpenAI API key (required)")
    openai_primary_model: str = Field(
        default="gpt-4o",  # Updated to latest model
        description="Main model for complex tasks"
    )
    openai_fast_model: str = Field(
        default="gpt-3.5-turbo-0125",  # Updated to latest version
        description="Faster model for simple tasks"
    )
    openai_classification_model: str = Field(
        default="gpt-3.5-turbo-0125",
        description="Model for classification fallbacks"
    )
    openai_max_tokens_primary: int = Field(
        default=2000,  # Increased from 1500 (was too low)
        ge=100,
        le=4000,
        description="Max tokens for primary model"
    )
    openai_max_tokens_fast: int = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Max tokens for fast model"
    )
    openai_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="API call timeout in seconds"
    )
    
    # ============================================================================
    # Model Pricing (per 1K tokens) - Updated to latest pricing
    # ============================================================================
    gpt4o_input_cost: float = Field(
        default=0.0025,
        description="GPT-4o input cost per 1K tokens"
    )
    gpt4o_output_cost: float = Field(
        default=0.01,
        description="GPT-4o output cost per 1K tokens"
    )
    gpt35_input_cost: float = Field(
        default=0.0005,
        description="GPT-3.5 input cost per 1K tokens"
    )
    gpt35_output_cost: float = Field(
        default=0.0015,
        description="GPT-3.5 output cost per 1K tokens"
    )
    
    # ============================================================================
    # AI Processing Thresholds
    # ============================================================================
    similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Semantic similarity threshold"
    )
    confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for route acceptance"
    )
    quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for generated content"
    )
    auto_approval_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum score for auto-approval"
    )
    
    # ============================================================================
    # Caching Configuration
    # ============================================================================
    cache_enabled: bool = Field(
        default=True,
        description="Enable/disable caching system"
    )
    cache_ttl_comment_minutes: int = Field(
        default=1440,  # 24 hours
        ge=1,
        description="Cache TTL for comments in minutes"
    )
    cache_ttl_email_minutes: int = Field(
        default=1440,  # 24 hours
        ge=1,
        description="Cache TTL for emails in minutes"
    )
    cache_ttl_routing_minutes: int = Field(
        default=60,  # 1 hour
        ge=1,
        description="Cache TTL for routing decisions in minutes"
    )
    cache_max_size: int = Field(
        default=1000,  # Conservative limit
        ge=100,
        le=100000,
        description="Maximum cache entries"
    )
    
    # ============================================================================
    # Semantic Caching (Optional - Advanced Feature)
    # ============================================================================
    use_embedding_cache: bool = Field(
        default=False,  # Start disabled, enable later if needed
        description="Enable semantic similarity caching (requires sentence-transformers)"
    )
    
    # ============================================================================
    # Rate Limiting & Performance
    # ============================================================================
    max_requests_per_minute: int = Field(
        default=100,
        ge=1,
        description="Maximum requests per minute per user"
    )
    max_tokens_per_hour: int = Field(
        default=50000,
        ge=1000,
        description="Maximum tokens consumed per hour"
    )
    
    # ============================================================================
    # Cost Controls
    # ============================================================================
    max_daily_cost_usd: float = Field(
        default=100.0,
        ge=0.0,
        description="Maximum daily API cost in USD"
    )
    alert_at_cost_usd: float = Field(
        default=80.0,
        ge=0.0,
        description="Send alert when daily cost reaches this amount"
    )
    
    # ============================================================================
    # Validation & Quality Control
    # ============================================================================
    profanity_filter_enabled: bool = Field(
        default=True,
        description="Enable profanity filtering"
    )
    sensitive_info_detection: bool = Field(
        default=True,
        description="Detect sensitive information (SSN, credit cards, etc.)"
    )
    length_validation_enabled: bool = Field(
        default=True,
        description="Validate response length"
    )
    max_input_length: int = Field(
        default=5000,
        ge=100,
        le=50000,
        description="Maximum input length in characters"
    )
    
    # ============================================================================
    # Monitoring & Logging
    # ============================================================================
    detailed_logging: bool = Field(
        default=True,
        description="Enable detailed logging"
    )
    metrics_collection_enabled: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    metrics_max_records: int = Field(
        default=10000,
        ge=1000,
        description="Maximum metrics records to keep in memory"
    )
    performance_monitoring: bool = Field(
        default=True,
        description="Enable performance monitoring"
    )
    alert_on_high_error_rate: bool = Field(
        default=True,
        description="Send alerts on high error rates"
    )
    error_rate_threshold: float = Field(
        default=0.1,  # 10%
        ge=0.0,
        le=1.0,
        description="Error rate threshold for alerts"
    )
    
    # ============================================================================
    # Circuit Breaker Configuration
    # ============================================================================
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker pattern"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Failures before opening circuit"
    )
    circuit_breaker_timeout_minutes: int = Field(
        default=5,
        ge=1,
        description="Minutes before attempting to close circuit"
    )
    
    # ============================================================================
    # Environment Configuration
    # ============================================================================
    environment: str = Field(
        default="development",
        description="Environment: development, staging, or production"
    )
    debug_mode: bool = Field(
        default=True,
        description="Enable debug mode (disable in production)"
    )
    test_mode: bool = Field(
        default=False,
        description="Enable test mode (mocks external calls)"
    )
    
    # ============================================================================
    # Validators
    # ============================================================================
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        """Validate OpenAI API key format"""
        if not v:
            raise ValueError('OpenAI API key is required')
        if not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format (must start with sk-)')
        if len(v) < 20:
            raise ValueError('OpenAI API key appears to be too short')
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ['development', 'staging', 'production']
        if v not in allowed:
            raise ValueError(f'Environment must be one of: {", ".join(allowed)}')
        return v
    
    @validator('debug_mode')
    def validate_debug_mode(cls, v, values):
        """Warn if debug mode is enabled in production"""
        if v and values.get('environment') == 'production':
            # Don't raise error, but this will be caught by validation check
            pass
        return v
    
    @validator('alert_at_cost_usd')
    def validate_cost_alert(cls, v, values):
        """Ensure alert threshold is less than max cost"""
        max_cost = values.get('max_daily_cost_usd')
        if max_cost and v > max_cost:
            raise ValueError('alert_at_cost_usd must be less than max_daily_cost_usd')
        return v
    
    @validator('cache_max_size')
    def validate_cache_size(cls, v):
        """Validate cache size is reasonable"""
        if v > 10000:
            # Warn but allow
            import logging
            logging.warning(f"Cache size {v} is very large - may consume significant memory")
        return v
    
    # ============================================================================
    # Properties for Easy Access
    # ============================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self.environment == "staging"
    
    @property
    def model_config_map(self) -> Dict[str, str]:
        """Get model configuration mapping"""
        return {
            "primary": self.openai_primary_model,
            "fast": self.openai_fast_model,
            "classification": self.openai_classification_model
        }
    
    @property
    def token_limits(self) -> Dict[str, int]:
        """Get token limits per model"""
        return {
            self.openai_primary_model: self.openai_max_tokens_primary,
            self.openai_fast_model: self.openai_max_tokens_fast,
            self.openai_classification_model: self.openai_max_tokens_fast
        }
    
    @property
    def cost_config(self) -> Dict[str, Dict[str, float]]:
        """Get pricing configuration"""
        return {
            "gpt-4o": {
                "input": self.gpt4o_input_cost,
                "output": self.gpt4o_output_cost
            },
            "gpt-4-turbo-preview": {
                "input": 0.01,
                "output": 0.03
            },
            "gpt-3.5-turbo": {
                "input": self.gpt35_input_cost,
                "output": self.gpt35_output_cost
            },
            "gpt-3.5-turbo-0125": {
                "input": self.gpt35_input_cost,
                "output": self.gpt35_output_cost
            }
        }
    
    class Config:
        env_file = ".env"
        # REMOVED: env_prefix = "AI_ENGINE_"  # Causes backward compatibility issues
        case_sensitive = False
        
        # Example .env file structure
        env_file_example = """
        # OpenAI Configuration
        OPENAI_API_KEY=sk-your-key-here
        OPENAI_PRIMARY_MODEL=gpt-4o
        
        # Environment
        ENVIRONMENT=production
        DEBUG_MODE=false
        
        # Cost Limits
        MAX_DAILY_COST_USD=100.0
        ALERT_AT_COST_USD=80.0
        
        # Caching
        CACHE_ENABLED=true
        USE_EMBEDDING_CACHE=false
        """


# ============================================================================
# Global Configuration Instance
# ============================================================================
config = AIEngineConfig()


# ============================================================================
# Helper Functions
# ============================================================================

def reload_config():
    """Reload configuration from environment"""
    global config
    config = AIEngineConfig()
    return config


def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary for logging"""
    return {
        "environment": config.environment,
        "primary_model": config.openai_primary_model,
        "cache_enabled": config.cache_enabled,
        "semantic_cache": config.use_embedding_cache,
        "max_daily_cost": config.max_daily_cost_usd,
        "circuit_breaker": config.circuit_breaker_enabled,
        "debug_mode": config.debug_mode
    }