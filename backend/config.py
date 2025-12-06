"""Application configuration settings."""

import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Find .env file in backend directory
backend_dir = Path(__file__).parent
env_file_path = backend_dir / ".env"


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "podcast_summarizer_backend"
    env: str = "development"
    
    # Tadata MCP Configuration
    tadata_mcp_url: str = "https://good-clubs-teach.mcp.tadata.com"
    TADATA_API_KEY: str = ""
    
    # Notion MCP Configuration
    notion_mcp_url: str = "https://quick-symbols-marry.mcp.tadata.com"
    NOTION_API_KEY: str = ""  # Can reuse TADATA_API_KEY or set separately
    notion_parent_page_id: str = ""  # Optional parent page ID (empty = workspace root)
    
    # Gradient AI Configuration
    model_access_key: str = ""
    # Available models: openai-gpt-oss-120b, gpt-oss-20b, claude-sonnet-4, llama-3.3-instruct-70b
    # Set GRADIENT_MODEL in .env to override (e.g., GRADIENT_MODEL=gpt-oss-20b)
    gradient_model: str = "openai-gpt-oss-120b"
    
    # YouTube Transcript Proxy (optional - for IP ban workaround)
    # Format: "http://user:pass@host:port" or "http://host:port"
    youtube_proxy: str = ""
    
    # YouTube Browser Cookies (for bot verification bypass)
    # Options: "chrome", "firefox", "safari", "edge", "brave", "opera", "vivaldi"
    # Or path to a cookies.txt file
    youtube_cookies_from_browser: str = ""
    
    model_config = SettingsConfigDict(
        env_file=str(env_file_path),
        case_sensitive=False,
        env_file_encoding="utf-8"
    )
    
    @property
    def tadata_api_key(self) -> str:
        """Get Tadata API key."""
        return self.TADATA_API_KEY
    
    @property
    def tadata_full_url(self) -> str:
        """Get full Tadata MCP URL with API key."""
        return f"{self.tadata_mcp_url}/?tadata-api-key={self.tadata_api_key}"
    
    @property
    def notion_api_key(self) -> str:
        """Get Notion API key (reuse Tadata key if Notion key not set)."""
        return self.NOTION_API_KEY if self.NOTION_API_KEY else self.TADATA_API_KEY
    
    @property
    def notion_full_url(self) -> str:
        """Get full Notion MCP URL with API key."""
        api_key = self.notion_api_key
        return f"{self.notion_mcp_url}/?tadata-api-key={api_key}"


settings = Settings()

# Debug logging
if env_file_path.exists():
    logger.info(f".env file found at: {env_file_path}")
    # Check if key exists in env file (without printing the actual key)
    with open(env_file_path, 'r') as f:
        env_content = f.read()
        if "TADATA_API_KEY" in env_content:
            logger.info("TADATA_API_KEY found in .env file")
        else:
            logger.warning("TADATA_API_KEY not found in .env file")
else:
    logger.warning(f".env file not found at: {env_file_path}")

# Check if key was loaded
if settings.TADATA_API_KEY:
    logger.info("TADATA_API_KEY loaded successfully (key present)")
else:
    logger.error("TADATA_API_KEY is empty! Check your .env file.")
