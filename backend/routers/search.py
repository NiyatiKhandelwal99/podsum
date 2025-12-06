"""Search endpoint for finding YouTube podcasts and generating summaries."""

import logging
from fastapi import APIRouter, HTTPException

from config import settings
from models.requests import SearchRequest
from models.responses import SearchResponse, YouTubeSummarizeResponse
from services.tadata import search_youtube_podcast
from services.youtube_summarizer import YouTubeSummarizer
from services.notion import save_summary_to_notion

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/search", response_model=YouTubeSummarizeResponse)
async def search(request: SearchRequest):
    """
    Search for a YouTube podcast based on a natural language query,
    then generate transcript and summary.
    
    Example queries:
    - "Joe Rogan podcast with Elon Musk"
    - "Lex Fridman interview with Sam Altman"
    - "Tim Ferriss podcast about productivity"
    - "Nikhil Kamath and Elon Musk podcast"
    """
    logger.info(f"Search request received with query: {request.query}")
    
    # Step 1: Search for YouTube URL using Tavily
    try:
        search_result = await search_youtube_podcast(request.query)
        youtube_url = search_result["youtube_url"]
        logger.info(f"Found YouTube URL: {youtube_url}")
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Could not find a YouTube podcast for: {request.query}"
        )
    
    # Step 2: Generate transcript and summary using YouTubeSummarizer
    if not settings.model_access_key:
        raise HTTPException(
            status_code=500,
            detail="Gradient AI model access key not configured. Set MODEL_ACCESS_KEY in your .env file."
        )
    
    try:
        summarizer = YouTubeSummarizer(
            model_access_key=settings.model_access_key,
            model=settings.gradient_model
        )
        
        result = await summarizer.summarize_video(youtube_url)
        
        logger.info(f"Successfully summarized video: {result.video_id} ({result.duration_minutes:.1f} min)")
        
        # Step 3: Save to Notion (non-blocking)
        notion_page_url = None
        saved_to_notion = False
        
        try:
            logger.info("[SEARCH] Attempting to save summary to Notion...")
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
                logger.info(f"[SEARCH] Summary saved to Notion: {notion_page_url}")
            else:
                logger.warning("[SEARCH] Notion save returned no URL")
        except Exception as e:
            logger.error(f"[SEARCH] Failed to save to Notion: {e}", exc_info=True)
            logger.warning("[SEARCH] Continuing without Notion save")
        
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
