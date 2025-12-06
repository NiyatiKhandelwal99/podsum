"""Request models for API endpoints."""

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    """Request model for the generate endpoint."""
    
    input: str

