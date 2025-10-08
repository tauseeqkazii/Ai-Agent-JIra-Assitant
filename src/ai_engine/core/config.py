"""
Enhanced AI Engine Configuration
Supports both OpenAI and Azure OpenAI
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings 
from typing import Dict, Any, Optional, Literal
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class AIEngineConfig(BaseSettings):
    """Complete AI Engine Configuration with Azure OpenAI Support"""
    
    # ============================================================================
    # API Provider Configuration (NEW)
    # ============================================================================
    api_provider: Literal["openai", "azure"] = Field(
        default="azure",
        description="API provider: 'openai' or 'azure'"
    )
    
    # ============================================================================
    # OpenAI Configuration (works for both OpenAI and Azure)
    # ============================================================================
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="OpenAI or Azure OpenAI API key"
    )
    
    # Azure-specific fields
    azure_api_base: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_BASE_URL", None),
        description="Azure OpenAI endpoint (e.g., https://your-resource.cognitiveservices.azure.com/openai/v1/)"
    )
    azure_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version"
    )
    azure_deployment_name_primary: Optional[str] = Field(
        default="gpt-4o-mini",
        description="Azure deployment name for primary model"
    )
    azure_deployment_name_fast: Optional[str] = Field(
        default="gpt-35-turbo",
        description="Azure deployment name for fast model"
    )
    azure_deployment_name_oss: Optional[str] = Field(
        default="gpt-oss-120b",
        description="Azure deployment name for OSS model"
    )
    
    # Model names (for OpenAI) or deployment names (for Azure)
    openai_primary_model: str = Field(
        default="gpt-4o-mini",
        description="Primary model name or Azure deployment name"
    )
    openai_fast_model: str = Field(
        default="gpt-35-turbo",
        description="Fast model name or Azure deployment name"
    )
    openai_classification_model: str = Field(
        default="gpt-35-turbo",
        description="Classification model name or Azure deployment name"
    )
    
    openai_max_tokens_primary: int = Field(default=2000, ge=100, le=4000)
    openai_max_tokens_fast: int = Field(default=1000, ge=100, le=4000)
    openai_timeout_seconds: int = Field(default=30, ge=5, le=120)
    
    # ============================================================================
    # Model Pricing (per 1K tokens)
    # ============================================================================
    gpt4o_input_cost: float = Field(default=0.0025)
    gpt4o_output_cost: float = Field(default=0.01)
    gpt35_input_cost: float = Field(default=0.0005)
    gpt35_output_cost: float = Field(default=0.0015)
    gpt4o_mini_input_cost: float = Field(default=0.0015)
    gpt4o_mini_output_cost: float = Field(default=0.002)
    gpt_oss_input_cost: float = Field(default=0.0005)
    gpt_oss_output_cost: float = Field(default=0.0015)
    
    # ============================================================================
    # AI Processing Thresholds
    # ============================================================================
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    auto_approval_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    
    # ============================================================================
    # Caching Configuration
    # ============================================================================
    cache_enabled: bool = Field(default=True)
    cache_ttl_comment_minutes: int = Field(default=1440, ge=1)
    cache_ttl_email_minutes: int = Field(default=1440, ge=1)
    cache_ttl_routing_minutes: int = Field(default=60, ge=1)
    cache_ttl_similarity_minutes: int = Field(default=60, ge=1)
    cache_max_size: int = Field(default=1000, ge=100, le=100000)
    use_embedding_cache: bool = Field(default=False)
    
    # ============================================================================
    # Rate Limiting & Performance
    # ============================================================================
    max_requests_per_minute: int = Field(default=100, ge=1)
    max_tokens_per_hour: int = Field(default=50000, ge=1000)
    batch_processing_enabled: bool = Field(default=True)
    batch_size: int = Field(default=5)
    
    # ============================================================================
    # Cost Controls
    # ============================================================================
    max_daily_cost_usd: float = Field(default=100.0, ge=0.0)
    alert_at_cost_usd: float = Field(default=80.0, ge=0.0)
    
    # ============================================================================
    # Validation & Quality Control
    # ============================================================================
    profanity_filter_enabled: bool = Field(default=True)
    sensitive_info_detection: bool = Field(default=True)
    length_validation_enabled: bool = Field(default=True)
    max_input_length: int = Field(default=5000, ge=100, le=50000)
    
    # ============================================================================
    # Monitoring & Logging
    # ============================================================================
    detailed_logging: bool = Field(default=True)
    metrics_collection_enabled: bool = Field(default=True)
    metrics_max_records: int = Field(default=10000, ge=1000)
    performance_monitoring: bool = Field(default=True)
    alert_on_high_error_rate: bool = Field(default=True)
    error_rate_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    
    # ============================================================================
    # Circuit Breaker Configuration
    # ============================================================================
    circuit_breaker_enabled: bool = Field(default=True)
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1)
    circuit_breaker_timeout_minutes: int = Field(default=5, ge=1)
    
    # ============================================================================
    # Environment Configuration
    # ============================================================================
    environment: str = Field(default="development")
    debug_mode: bool = Field(default=True)
    test_mode: bool = Field(default=False)
    
    # ============================================================================
    # Validators
    # ============================================================================
    
    @field_validator('openai_api_key')
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """Validate API key format"""
        if not v:
            raise ValueError('API key is required')
        
        # Azure keys don't start with 'sk-', they're longer alphanumeric strings
        # OpenAI keys start with 'sk-'
        if len(v) < 20:
            raise ValueError('API key appears to be too short')
        
        return v
    
    @field_validator('azure_api_base')
    @classmethod
    def validate_azure_base(cls, v: Optional[str], info) -> Optional[str]:
        """Validate Azure API base URL if using Azure"""
        values = info.data
        if values.get('api_provider') == 'azure' and not v:
            raise ValueError('azure_api_base is required when using Azure OpenAI')
        
        if v and not v.startswith('https://'):
            raise ValueError('azure_api_base must start with https://')
        
        return v
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        allowed = ['development', 'staging', 'production']
        if v not in allowed:
            raise ValueError(f'Environment must be one of: {", ".join(allowed)}')
        return v
    
    @field_validator('alert_at_cost_usd')
    @classmethod
    def validate_cost_alert(cls, v: float, info) -> float:
        """Ensure alert threshold is less than max cost"""
        max_cost = info.data.get('max_daily_cost_usd')
        if max_cost and v > max_cost:
            raise ValueError('alert_at_cost_usd must be less than max_daily_cost_usd')
        return v
    
    # ============================================================================
    # Properties for Easy Access
    # ============================================================================
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_azure(self) -> bool:
        """Check if using Azure OpenAI"""
        return self.api_provider == "azure"
    
    @property
    def model_config_map(self) -> Dict[str, str]:
        """Get model/deployment configuration mapping"""
        if self.is_azure:
            return {
                "primary": self.azure_deployment_name_primary,
                "fast": self.azure_deployment_name_fast,
                "oss": self.azure_deployment_name_oss,
                "classification": self.azure_deployment_name_fast
            }
        else:
            return {
                "primary": self.openai_primary_model,
                "fast": self.openai_fast_model,
                "classification": self.openai_classification_model
            }
    
    @property
    def model_info(self) -> Dict[str, Any]:
        return self.model_config_map
    
    @property
    def token_limits(self) -> Dict[str, int]:
        """Get token limits per model"""
        models = self.model_config_map
        return {
            models["primary"]: self.openai_max_tokens_primary,
            models["fast"]: self.openai_max_tokens_fast,
            models["classification"]: self.openai_max_tokens_fast
        }
    
    @property
    def cost_config(self) -> Dict[str, Dict[str, float]]:
        """Get pricing configuration"""
        return {
            "gpt-4o-mini": {
                "input": self.gpt4o_mini_input_cost,
                "output": self.gpt4o_mini_output_cost
            },
            "gpt-35-turbo": {
                "input": self.gpt35_input_cost,
                "output": self.gpt35_output_cost
            },
            "gpt-oss-120b": {
                "input": self.gpt_oss_input_cost,
                "output": self.gpt_oss_output_cost
            }
        }
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


# ============================================================================
# Global Configuration Instance
# ============================================================================
config = AIEngineConfig()

# Log configuration on startup
if config.debug_mode:
    logger.info(f"AI Engine initialized with provider: {config.api_provider}")
    if config.is_azure:
        logger.info(f"Azure endpoint: {config.azure_api_base}")


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
        "api_provider": config.api_provider,
        "environment": config.environment,
        "primary_model": config.openai_primary_model,
        "azure_endpoint": config.azure_api_base if config.is_azure else None,
        "cache_enabled": config.cache_enabled,
        "max_daily_cost": config.max_daily_cost_usd,
        "debug_mode": config.debug_mode
    }


# Export for backward compatibility
settings = config
__all__ = ['config', 'settings', 'AIEngineConfig', 'reload_config', 'get_config_summary']