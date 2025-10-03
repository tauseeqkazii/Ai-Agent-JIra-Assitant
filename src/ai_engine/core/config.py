from typing import Dict, Any, Optional, List
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator


class AIEngineConfig(BaseSettings):
    """Complete AI Engine Configuration"""
    
    # OpenAI Configuration
    # openai_api_key: str = os.getenv("OPENAI_API_KEY")
    openai_primary_model: str = "gpt-4-turbo-preview"
    openai_fast_model: str = "gpt-3.5-turbo"
    openai_classification_model: str = "gpt-3.5-turbo"
    openai_max_tokens_primary: int = 1500
    openai_max_tokens_fast: int = 1000
    openai_timeout_seconds: int = 30
    
    # AI Processing Thresholds
    similarity_threshold: float = 0.85
    confidence_threshold: float = 0.8
    quality_threshold: float = 0.7
    auto_approval_threshold: float = 0.8
    
    # Caching Configuration
    cache_enabled: bool = True
    cache_ttl_comment_minutes: int = 1440  # 24 hours
    cache_ttl_similarity_minutes: int = 60  # 1 hour
    cache_max_size: int = 10000
    
    # Rate Limiting & Performance
    max_requests_per_minute: int = 100
    max_tokens_per_hour: int = 50000
    batch_processing_enabled: bool = True
    batch_size: int = 5
    
    # Validation & Quality Control
    profanity_filter_enabled: bool = True
    sensitive_info_detection: bool = True
    length_validation_enabled: bool = True
    
    # Monitoring & Logging
    detailed_logging: bool = True
    metrics_collection_enabled: bool = True
    performance_monitoring: bool = True
    alert_on_high_error_rate: bool = True
    error_rate_threshold: float = 0.1  # 10%
    
    # Production Optimizations
    use_embedding_cache: bool = True
    enable_prompt_compression: bool = True
    fallback_enabled: bool = True
    graceful_degradation: bool = True
    
    # Development vs Production
    environment: str = "development"  # development/staging/production
    debug_mode: bool = True
    test_mode: bool = False
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        if not v or not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format')
        return v
    
    @validator('confidence_threshold', 'quality_threshold', 'auto_approval_threshold')
    def validate_thresholds(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Thresholds must be between 0.0 and 1.0')
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def model_info(self) -> Dict[str, Any]:
        return {
            "primary": self.openai_primary_model,
            "fast": self.openai_fast_model, 
            "classification": self.openai_classification_model
        }
    
    @property
    def token_limits(self) -> Dict[str, int]:
        return {
            self.openai_primary_model: self.openai_max_tokens_primary,
            self.openai_fast_model: self.openai_max_tokens_fast,
            self.openai_classification_model: self.openai_max_tokens_fast
        }
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_ENGINE_",
        extra="ignore" 
)

# Global config instance
config = AIEngineConfig()
settings = config
__all__ = ['config', 'settings', 'AIEngineConfig']