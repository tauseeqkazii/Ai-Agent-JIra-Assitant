from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    openai_max_tokens: int = 3500
    openai_timeout: int = 30
    
    # Thresholds
    similarity_threshold: float = 0.85
    confidence_threshold: float = 0.8
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Development
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
