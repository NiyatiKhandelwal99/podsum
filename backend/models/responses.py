"""Response models for API endpoints."""

from pydantic import BaseModel, Field


class GenerateResponse(BaseModel):
    """Response model for the generate endpoint."""
    
    video_url: str
    episode_title: str
    summary: str
    bullets: list[str]
    ig_carousel: list[dict]
    saved_to_notion: bool


class YouTubeSummarizeResponse(BaseModel):
    """Response model for YouTube video summarization."""
    
    video_id: str = Field(..., description="YouTube video ID")
    video_url: str = Field(..., description="Full YouTube video URL")
    title: str = Field(..., description="Video title")
    transcript_length: int = Field(..., description="Length of transcript in characters")
    duration_minutes: float = Field(..., description="Video duration in minutes")
    summary: str = Field(..., description="Comprehensive summary of the video")
    top_learnings: list[str] = Field(
        ..., 
        description="Top 5 key learnings from the video",
        min_length=5,
        max_length=5
    )

