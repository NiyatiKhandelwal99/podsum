"""YouTube video summarization endpoint."""

import logging
from fastapi import APIRouter, HTTPException

from config import settings
from models.requests import YouTubeSummarizeRequest
from models.responses import YouTubeSummarizeResponse
from services.youtube_summarizer import YouTubeSummarizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube", tags=["YouTube"])


@router.post("/summarize", response_model=YouTubeSummarizeResponse)
async def summarize_youtube_video(request: YouTubeSummarizeRequest):
    """
    Extract transcript from a YouTube video and generate a summary with top 5 learnings.
    
    Supports long videos (2-3+ hours). The transcript is automatically chunked and 
    processed to generate a comprehensive summary.
    
    **Note**: Requires a valid Gradient AI model access key configured in the environment.
    """
    if not settings.model_access_key:
        raise HTTPException(
            status_code=500,
            detail="Gradient AI model access key not configured. Set MODEL_ACCESS_KEY in your .env file."
        )
    
    logger.info(f"Summarization request received for URL: {request.url}")
    
    try:
        summarizer = YouTubeSummarizer(
            model_access_key=settings.model_access_key,
            model=settings.gradient_model
        )
        
        result = await summarizer.summarize_video(request.url)
        
        logger.info(f"Successfully summarized video: {result.video_id} ({result.duration_minutes:.1f} min)")
        
        return YouTubeSummarizeResponse(
            video_id=result.video_id,
            video_url=result.video_url,
            title=result.title,
            transcript_length=result.transcript_length,
            duration_minutes=result.duration_minutes,
            summary=result.summary,
            top_learnings=result.top_learnings
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error summarizing video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize video: {str(e)}")

