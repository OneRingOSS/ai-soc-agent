"""Configuration management for SOC Agent System."""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load .env file from backend directory (but NOT during testing)
# This prevents tests from accidentally using real OpenAI API
if not os.getenv("TESTING"):
    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # CORS Configuration
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    
    # Threat Generation
    threat_generation_interval: int = Field(default=30, env="THREAT_GENERATION_INTERVAL")
    max_stored_threats: int = Field(default=100, env="MAX_STORED_THREATS")

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # LLM Configuration
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1000, env="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=30, env="LLM_TIMEOUT")

    class Config:
        # Don't auto-load .env file here - we handle it manually above
        # to prevent loading during tests (when TESTING=1)
        extra = "ignore"  # Ignore extra fields in .env file


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


settings = get_settings()

