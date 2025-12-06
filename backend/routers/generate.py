"""Generate endpoint for podcast summarization."""

import logging
from fastapi import APIRouter

from models.requests import GenerateRequest
from models.responses import GenerateResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate podcast summary and content."""
    logger.info(f"Generate request received with input length: {len(request.input)}")
    
    # Static placeholder response
    response = GenerateResponse(
        video_url="https://www.youtube.com/watch?v=dummy",
        episode_title="Dummy Episode Title",
        summary="This is a placeholder summary. In a real implementation, this would contain an AI-generated summary of the podcast episode.",
        bullets=[
            "Key point 1: This is a placeholder bullet point",
            "Key point 2: Another example bullet point",
            "Key point 3: Final placeholder bullet point"
        ],
        ig_carousel=[
            {
                "type": "text",
                "text": "Welcome to this episode! Here's what we'll cover today."
            },
            {
                "type": "text",
                "text": "Main topic discussion with key insights and takeaways."
            },
            {
                "type": "text",
                "text": "Don't forget to subscribe for more content!"
            }
        ],
        saved_to_notion=False
    )
    
    logger.info("Returning placeholder response")
    return response

