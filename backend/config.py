"""Application configuration settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "podcast_summarizer_backend"
    env: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

