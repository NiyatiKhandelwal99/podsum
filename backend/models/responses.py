"""Response models for API endpoints."""

from pydantic import BaseModel


class GenerateResponse(BaseModel):
    """Response model for the generate endpoint."""
    
    video_url: str
    episode_title: str
    summary: str
    bullets: list[str]
    ig_carousel: list[dict]
    saved_to_notion: bool

