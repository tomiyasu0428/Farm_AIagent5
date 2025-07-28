"""Configuration settings for the Agricultural AI Agent system."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_uri: str = Field(..., env="MONGODB_URI")
    mongodb_database: str = Field(default="agri_ai_db", env="MONGODB_DATABASE")
    
    # LINE Bot Configuration
    line_channel_access_token: str = Field(..., env="LINE_CHANNEL_ACCESS_TOKEN")
    line_channel_secret: str = Field(..., env="LINE_CHANNEL_SECRET")
    
    # Google Cloud Configuration
    google_cloud_project: str = Field(..., env="GOOGLE_CLOUD_PROJECT")
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    
    # LangSmith Configuration (Optional)
    langchain_tracing_v2: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    langchain_endpoint: Optional[str] = Field(default=None, env="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_project: Optional[str] = Field(default="agri-ai-agent", env="LANGCHAIN_PROJECT")
    
    # Application Configuration
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()