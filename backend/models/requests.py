"""Request models for API endpoints."""

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request model for the generate endpoint."""
    
    input: str


class YouTubeSummarizeRequest(BaseModel):
    """Request model for YouTube video summarization."""
    
    url: str = Field(
        ...,
        description="YouTube video URL",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    )

