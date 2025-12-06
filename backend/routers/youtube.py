"""YouTube video summarization endpoint."""

import logging
from fastapi import APIRouter, HTTPException

from config import settings
from models.requests import YouTubeSummarizeRequest
from models.responses import YouTubeSummarizeResponse
from services.youtube_summarizer import YouTubeSummarizer
from services.notion import save_summary_to_notion

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
            model=settings.gradient_model,
            proxy=settings.youtube_proxy,
            cookies_from_browser=settings.youtube_cookies_from_browser
        )
        
        result = await summarizer.summarize_video(request.url)
        
        logger.info(f"Successfully summarized video: {result.video_id} ({result.duration_minutes:.1f} min)")
        
        # Save to Notion (non-blocking)
        notion_page_url = None
        saved_to_notion = False
        
        try:
            logger.info("[YOUTUBE] Attempting to save summary to Notion...")
            notion_page_url = await save_summary_to_notion(
                title=result.title,
                video_url=result.video_url,
                video_id=result.video_id,
                duration_minutes=result.duration_minutes,
                transcript_length=result.transcript_length,
                summary=result.summary,
                top_learnings=result.top_learnings
            )
            
            if notion_page_url:
                saved_to_notion = True
                logger.info(f"[YOUTUBE] Summary saved to Notion: {notion_page_url}")
            else:
                logger.warning("[YOUTUBE] Notion save returned no URL")
        except Exception as e:
            logger.error(f"[YOUTUBE] Failed to save to Notion: {e}", exc_info=True)
            logger.warning("[YOUTUBE] Continuing without Notion save")
        
        return YouTubeSummarizeResponse(
            video_id=result.video_id,
            video_url=result.video_url,
            title=result.title,
            transcript_length=result.transcript_length,
            duration_minutes=result.duration_minutes,
            summary=result.summary,
            top_learnings=result.top_learnings,
            notion_page_url=notion_page_url,
            saved_to_notion=saved_to_notion
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error summarizing video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize video: {str(e)}")

