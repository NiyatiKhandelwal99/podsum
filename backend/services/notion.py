"""Notion MCP service for saving podcast summaries to Notion pages."""

import logging
import time
from datetime import datetime
from typing import Optional
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import settings

logger = logging.getLogger(__name__)

# Global Notion MCP client instance
_notion_mcp_client: MultiServerMCPClient | None = None


def _get_notion_mcp_client() -> Optional[MultiServerMCPClient]:
    """Get or create the Notion MCP client singleton."""
    global _notion_mcp_client
    
    logger.info("=" * 80)
    logger.info("[NOTION CLIENT] Getting Notion MCP client instance")
    
    if _notion_mcp_client is None:
        api_key = settings.notion_api_key
        notion_url = settings.notion_mcp_url
        full_url = settings.notion_full_url
        
        logger.info("[NOTION CLIENT] Checking configuration...")
        logger.info(f"[NOTION CLIENT] Notion MCP URL: {notion_url}")
        logger.info(f"[NOTION CLIENT] API key configured: {bool(api_key)}")
        logger.info(f"[NOTION CLIENT] API key length: {len(api_key) if api_key else 0} characters")
        logger.info(f"[NOTION CLIENT] API key source: {'NOTION_API_KEY' if settings.NOTION_API_KEY else 'TADATA_API_KEY (fallback)'}")
        
        # Log API key preview safely
        if api_key:
            if len(api_key) > 20:
                logger.info(f"[NOTION CLIENT] API key preview: {api_key[:10]}...{api_key[-10:]}")
            else:
                logger.warning(f"[NOTION CLIENT] API key seems too short: {len(api_key)} chars")
        
        # Log full URL with masked key
        if "=" in full_url:
            url_base, url_key = full_url.split("=", 1)
            logger.info(f"[NOTION CLIENT] Full URL base: {url_base}")
            logger.info(f"[NOTION CLIENT] Full URL key (masked): ...{url_key[-10:] if len(url_key) > 10 else 'SHORT'}")
        else:
            logger.warning(f"[NOTION CLIENT] Full URL doesn't contain '=' separator: {full_url}")
        
        if not api_key:
            logger.error("[NOTION CLIENT] Notion API key not configured!")
            logger.error("[NOTION CLIENT] Set NOTION_API_KEY in .env file, or it will use TADATA_API_KEY")
            logger.warning("[NOTION CLIENT] Notion integration unavailable")
            logger.info("=" * 80)
            return None
        
        if not notion_url:
            logger.error("[NOTION CLIENT] Notion MCP URL not configured!")
            logger.info("=" * 80)
            return None
        
        # Validate API key format (Tadata keys typically start with 'tdk_')
        if not api_key.startswith("tdk_"):
            logger.warning(f"[NOTION CLIENT] API key doesn't start with 'tdk_' - format might be incorrect")
            logger.warning(f"[NOTION CLIENT] Expected format: tdk_...")
        
        logger.info("[NOTION CLIENT] Initializing new Notion MCP client...")
        logger.info(f"[NOTION CLIENT] Using transport: streamable_http")
        logger.info(f"[NOTION CLIENT] Target URL base: {notion_url}")
        
        try:
            start_time = time.time()
            logger.debug(f"[NOTION CLIENT] Creating MultiServerMCPClient with config:")
            logger.debug(f"[NOTION CLIENT]   Server name: 'notion'")
            logger.debug(f"[NOTION CLIENT]   Transport: 'streamable_http'")
            logger.debug(f"[NOTION CLIENT]   URL: {full_url.split('=')[0]}=[MASKED]")
            
            _notion_mcp_client = MultiServerMCPClient(
                {
                    "notion": {
                        "transport": "streamable_http",
                        "url": full_url
                    }
                }
            )
            init_time = time.time() - start_time
            logger.info(f"[NOTION CLIENT] ✓ Notion MCP client initialized successfully in {init_time:.2f}s")
            logger.debug(f"[NOTION CLIENT] Client type: {type(_notion_mcp_client)}")
            logger.info("=" * 80)
        except Exception as e:
            init_time = time.time() - start_time
            logger.error("=" * 80)
            logger.error(f"[NOTION CLIENT] ✗ Failed to initialize Notion MCP client after {init_time:.2f}s")
            logger.error(f"[NOTION CLIENT] Error type: {type(e).__name__}")
            logger.error(f"[NOTION CLIENT] Error message: {str(e)}")
            logger.error(f"[NOTION CLIENT] This might be due to:")
            logger.error(f"[NOTION CLIENT]   1. Invalid API key for Notion MCP server")
            logger.error(f"[NOTION CLIENT]   2. Notion MCP server URL incorrect")
            logger.error(f"[NOTION CLIENT]   3. Network connectivity issues")
            logger.error(f"[NOTION CLIENT]   4. Notion MCP server requires different authentication")
            logger.error(f"[NOTION CLIENT]   5. API key doesn't have permissions for Notion MCP")
            logger.error(f"[NOTION CLIENT] Full error traceback:")
            logger.exception(e)
            logger.error("=" * 80)
            _notion_mcp_client = None
            return None
    else:
        logger.debug("[NOTION CLIENT] Reusing existing Notion MCP client instance")
    
    logger.info("[NOTION CLIENT] Notion MCP client ready")
    return _notion_mcp_client


def _format_summary_for_notion(
    title: str,
    video_url: str,
    video_id: str,
    duration_minutes: float,
    transcript_length: int,
    summary: str,
    top_learnings: list[str]
) -> dict:
    """
    Format summary data into Notion page structure.
    
    Returns a dict with page properties and blocks ready for Notion API.
    """
    logger.debug("[NOTION] Formatting summary for Notion")
    
    # Format date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Create page title
    page_title = title if title else f"Podcast Summary - {video_id}"
    
    # Format blocks structure
    blocks = []
    
    # Callout block for video information
    video_info_text = f"⏱️ Duration: {duration_minutes:.1f} minutes\n🎥 YouTube: {video_url}\n📅 Date: {current_date}"
    blocks.append({
        "type": "callout",
        "callout": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": video_info_text}
                }
            ],
            "icon": {"emoji": "💡"}
        }
    })
    
    # Divider
    blocks.append({"type": "divider", "divider": {}})
    
    # Summary section
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Summary"}}]
        }
    })
    
    # Split summary into paragraphs for better formatting
    summary_paragraphs = summary.split("\n\n")
    for para in summary_paragraphs:
        if para.strip():
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": para.strip()}}]
                }
            })
    
    # Divider
    blocks.append({"type": "divider", "divider": {}})
    
    # Key Learnings section
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Key Learnings"}}]
        }
    })
    
    # Bulleted list for learnings
    for learning in top_learnings:
        blocks.append({
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": learning}}]
            }
        })
    
    # Divider
    blocks.append({"type": "divider", "divider": {}})
    
    # Video Details section
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Video Details"}}]
        }
    })
    
    # Video details as formatted paragraphs
    details_items = [
        ("Video ID", video_id),
        ("Transcript Length", f"{transcript_length:,} characters"),
        ("Duration", f"{duration_minutes:.1f} minutes"),
    ]
    
    for label, value in details_items:
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": f"{label}: "},
                        "annotations": {"bold": True}
                    },
                    {
                        "type": "text",
                        "text": {"content": value}
                    }
                ]
            }
        })
    
    # YouTube URL as a link
    blocks.append({
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": "YouTube URL: "},
                    "annotations": {"bold": True}
                },
                {
                    "type": "text",
                    "text": {"content": video_url},
                    "annotations": {"link": {"url": video_url}}
                }
            ]
        }
    })
    
    logger.debug(f"[NOTION] Formatted {len(blocks)} blocks for Notion page")
    
    return {
        "title": page_title,
        "blocks": blocks
    }


async def save_summary_to_notion(
    title: str,
    video_url: str,
    video_id: str,
    duration_minutes: float,
    transcript_length: int,
    summary: str,
    top_learnings: list[str]
) -> Optional[str]:
    """
    Save podcast summary to a new Notion page.
    
    Args:
        title: Episode title
        video_url: YouTube video URL
        video_id: YouTube video ID
        duration_minutes: Video duration in minutes
        transcript_length: Transcript length in characters
        summary: Summary text
        top_learnings: List of top 5 learnings
        
    Returns:
        Notion page URL if successful, None otherwise
    """
    save_start_time = time.time()
    logger.info("[NOTION] Starting Notion save process")
    logger.debug(f"[NOTION] Video ID: {video_id}, Title: {title[:50]}...")
    
    client = _get_notion_mcp_client()
    if not client:
        logger.warning("[NOTION] Notion MCP client unavailable, skipping Notion save")
        return None
    
    try:
        # Get available tools
        logger.info("=" * 80)
        logger.info("[NOTION] Fetching available Notion tools from MCP server...")
        logger.info(f"[NOTION] Client type: {type(client)}")
        logger.info(f"[NOTION] Client URL base: {settings.notion_mcp_url}")
        logger.info(f"[NOTION] API key source: {'NOTION_API_KEY' if settings.NOTION_API_KEY else 'TADATA_API_KEY (fallback)'}")
        
        tools_start = time.time()
        try:
            logger.debug("[NOTION] Calling client.get_tools()...")
            tools = await client.get_tools()
            tools_time = time.time() - tools_start
            logger.info(f"[NOTION] ✓ Tool fetch completed in {tools_time:.2f}s")
            logger.info(f"[NOTION] Found {len(tools)} available Notion tools")
            if tools:
                logger.info(f"[NOTION] Available tools: {[t.name for t in tools]}")
            else:
                logger.warning("[NOTION] ⚠ No tools returned! This might indicate an authentication issue.")
        except Exception as tools_error:
            tools_time = time.time() - tools_start
            
            # Check if this is an ExceptionGroup (has 'exceptions' attribute)
            is_exception_group = hasattr(tools_error, 'exceptions') and isinstance(tools_error.exceptions, (list, tuple))
            
            logger.error("=" * 80)
            logger.error(f"[NOTION] ✗ Failed to fetch tools after {tools_time:.2f}s")
            
            if is_exception_group:
                logger.error(f"[NOTION] Error type: ExceptionGroup ({len(tools_error.exceptions)} sub-exceptions)")
                
                # Extract the actual HTTP error from ExceptionGroup
                actual_error = None
                for exc in tools_error.exceptions:
                    logger.error(f"[NOTION]   Sub-exception: {type(exc).__name__}: {str(exc)}")
                    if "401" in str(exc) or "Unauthorized" in str(exc):
                        actual_error = exc
                    elif hasattr(exc, 'response') and hasattr(exc.response, 'status_code'):
                        if exc.response.status_code == 401:
                            actual_error = exc
                
                if actual_error:
                    logger.error("[NOTION] Authentication error detected (401 Unauthorized)")
                    logger.error("[NOTION] Detailed error information:")
                    logger.error(f"[NOTION]   Error type: {type(actual_error).__name__}")
                    logger.error(f"[NOTION]   Error message: {str(actual_error)}")
                    
                    # Try to extract more details from HTTP error
                    if hasattr(actual_error, 'response'):
                        logger.error(f"[NOTION]   HTTP status: {actual_error.response.status_code}")
                        logger.error(f"[NOTION]   HTTP URL: {actual_error.response.url if hasattr(actual_error.response, 'url') else 'N/A'}")
                        if hasattr(actual_error.response, 'text'):
                            try:
                                error_text = actual_error.response.text[:500]
                                logger.error(f"[NOTION]   Response text: {error_text}")
                            except:
                                pass
            else:
                logger.error(f"[NOTION] Error type: {type(tools_error).__name__}")
                logger.error(f"[NOTION] Error message: {str(tools_error)}")
                actual_error = tools_error
            
            # Check for 401 in error message or response
            error_str = str(tools_error).lower()
            has_401 = ("401" in error_str or "unauthorized" in error_str or
                      (hasattr(tools_error, 'response') and hasattr(tools_error.response, 'status_code') and 
                       tools_error.response.status_code == 401))
            
            if has_401 or (actual_error and ("401" in str(actual_error) or "Unauthorized" in str(actual_error))):
                logger.error("[NOTION] Authentication error detected (401 Unauthorized)")
                logger.error("[NOTION] Possible causes:")
                logger.error("[NOTION]   1. API key is incorrect or expired")
                logger.error("[NOTION]   2. API key doesn't have access to Notion MCP server")
                logger.error("[NOTION]   3. Notion MCP server requires separate authentication")
                logger.error("[NOTION]   4. API key format is incorrect")
                logger.error("[NOTION]   5. API key needs to be regenerated in Tadata dashboard")
                logger.error(f"[NOTION] Current API key source: {'NOTION_API_KEY' if settings.NOTION_API_KEY else 'TADATA_API_KEY'}")
                logger.error(f"[NOTION] Current API key length: {len(settings.notion_api_key)} characters")
                logger.error(f"[NOTION] Current API key preview: {settings.notion_api_key[:10]}...{settings.notion_api_key[-10:] if len(settings.notion_api_key) > 20 else 'SHORT'}")
                logger.error(f"[NOTION] Notion MCP URL: {settings.notion_mcp_url}")
                logger.error(f"[NOTION] Full URL (masked): {settings.notion_full_url.split('=')[0]}=[MASKED]")
                logger.error("[NOTION] Troubleshooting steps:")
                logger.error("[NOTION]   1. Verify NOTION_API_KEY in .env file matches Tadata dashboard")
                logger.error("[NOTION]   2. Check that API key has Notion MCP permissions enabled")
                logger.error("[NOTION]   3. Try regenerating the API key in Tadata dashboard")
                logger.error("[NOTION]   4. Ensure the Notion MCP server URL is correct")
            
            logger.error("=" * 80)
            raise
        
        # Find Notion page creation tool
        logger.info("[NOTION] Searching for Notion tools...")
        create_tool = None
        append_tool = None
        update_tool = None
        
        for i, tool in enumerate(tools, 1):
            tool_name_lower = tool.name.lower()
            logger.info(f"[NOTION] Tool {i}/{len(tools)}: '{tool.name}'")
            logger.debug(f"[NOTION]   Tool type: {type(tool)}")
            logger.debug(f"[NOTION]   Tool name (lowercase): '{tool_name_lower}'")
            
            # Check for page creation tools
            if "create" in tool_name_lower and "page" in tool_name_lower:
                create_tool = tool
                logger.info(f"[NOTION] ✓ Found page creation tool: '{tool.name}'")
            elif "create" in tool_name_lower:
                logger.debug(f"[NOTION]   Tool '{tool.name}' contains 'create' but not 'page'")
            
            # Check for block/content tools
            if "append" in tool_name_lower or "add" in tool_name_lower or "block" in tool_name_lower:
                append_tool = tool
                logger.info(f"[NOTION] ✓ Found block append tool: '{tool.name}'")
            
            # Check for update tools
            if "update" in tool_name_lower or "edit" in tool_name_lower:
                update_tool = tool
                logger.info(f"[NOTION] ✓ Found update tool: '{tool.name}'")
        
        logger.info(f"[NOTION] Tool discovery complete:")
        logger.info(f"[NOTION]   Page creation tool: {'Found' if create_tool else 'NOT FOUND'}")
        logger.info(f"[NOTION]   Block append tool: {'Found' if append_tool else 'NOT FOUND'}")
        logger.info(f"[NOTION]   Update tool: {'Found' if update_tool else 'NOT FOUND'}")
        
        if not create_tool:
            logger.error("[NOTION] Page creation tool not found!")
            logger.error(f"[NOTION] This means we cannot create Notion pages")
            logger.error(f"[NOTION] Available tools were: {[t.name for t in tools]}")
            logger.error(f"[NOTION] Please check:")
            logger.error(f"[NOTION]   1. Notion MCP server is properly configured")
            logger.error(f"[NOTION]   2. API key has correct permissions")
            logger.error(f"[NOTION]   3. Notion MCP server URL is correct")
            return None
        
        # Format content
        logger.debug("[NOTION] Formatting content for Notion...")
        formatted = _format_summary_for_notion(
            title=title,
            video_url=video_url,
            video_id=video_id,
            duration_minutes=duration_minutes,
            transcript_length=transcript_length,
            summary=summary,
            top_learnings=top_learnings
        )
        
        # Create page
        logger.info("=" * 80)
        logger.info("[NOTION PAGE] Starting page creation")
        logger.info(f"[NOTION PAGE] Page title: '{formatted['title']}'")
        logger.info(f"[NOTION PAGE] Number of blocks to add: {len(formatted['blocks'])}")
        logger.debug(f"[NOTION PAGE] Parent page ID: {settings.notion_parent_page_id or 'None (workspace root)'}")
        
        # Inspect tool schema to understand expected format
        logger.debug("[NOTION PAGE] Inspecting tool schema...")
        if hasattr(create_tool, 'args_schema'):
            logger.debug(f"[NOTION PAGE] Tool has args_schema: {create_tool.args_schema}")
        if hasattr(create_tool, 'description'):
            logger.debug(f"[NOTION PAGE] Tool description: {create_tool.description}")
        
        # Prepare page creation parameters based on error message
        # The tool expects 'pages' array, not 'title' property
        # Parent needs specific structure based on type
        
        # Build parent configuration
        if settings.notion_parent_page_id:
            # Parent is a specific page
            parent_config = {
                "type": "page_id",
                "page_id": settings.notion_parent_page_id
            }
            logger.info(f"[NOTION PAGE] Using parent page: {settings.notion_parent_page_id[:8]}...")
        else:
            # Try workspace root - but may need different format
            # Based on error, workspace might not be supported, so try without parent
            parent_config = None
            logger.info("[NOTION PAGE] No parent specified, will try different parent formats")
        
        create_start = time.time()
        create_result = None
        create_error = None
        
        # Try different parent formats if first attempt fails
        parent_formats_to_try = []
        
        if settings.notion_parent_page_id:
            # Try with page_id parent
            parent_formats_to_try.append({
                "type": "page_id",
                "page_id": settings.notion_parent_page_id
            })
        else:
            # Try different workspace formats
            parent_formats_to_try.append(None)  # No parent (try without parent first)
            parent_formats_to_try.append({"type": "workspace"})
            # Some APIs might need workspace_id
            parent_formats_to_try.append({"type": "workspace", "workspace": True})
        
        logger.info(f"[NOTION PAGE] Will try {len(parent_formats_to_try)} different parent format(s)")
        
        for attempt, try_parent in enumerate(parent_formats_to_try, 1):
            try:
                logger.info(f"[NOTION PAGE] Attempt {attempt}/{len(parent_formats_to_try)}: {'with parent' if try_parent else 'without parent'}")
                
                # Build page object
                page_object = {
                    "properties": {
                        "title": [
                            {
                                "text": {
                                    "content": formatted["title"]
                                }
                            }
                        ]
                    },
                    "children": formatted["blocks"]
                }
                
                # Add parent if specified
                if try_parent:
                    page_object["parent"] = try_parent
                    logger.debug(f"[NOTION PAGE]   Parent config: {try_parent}")
                
                create_params = {
                    "pages": [page_object]
                }
                
                logger.debug(f"[NOTION PAGE]   Invoking tool with params: pages array with {len(create_params['pages'])} page(s)")
                
                create_result = await create_tool.ainvoke(create_params)
                create_time = time.time() - create_start
                
                logger.info(f"[NOTION PAGE] ✓ Page creation succeeded on attempt {attempt} in {create_time:.2f}s")
                logger.info(f"[NOTION PAGE] Result type: {type(create_result)}")
                logger.debug(f"[NOTION PAGE] Result object: {create_result}")
                logger.debug(f"[NOTION PAGE] Result string preview: {str(create_result)[:500]}...")
                
                # Log result attributes if available
                if hasattr(create_result, '__dict__'):
                    logger.debug(f"[NOTION PAGE] Result attributes: {list(create_result.__dict__.keys())}")
                if hasattr(create_result, '__class__'):
                    logger.debug(f"[NOTION PAGE] Result class: {create_result.__class__.__name__}")
                
                # Success! Break out of retry loop
                break
                
            except Exception as attempt_error:
                create_time = time.time() - create_start
                logger.warning(f"[NOTION PAGE] Attempt {attempt} failed after {create_time:.2f}s")
                logger.warning(f"[NOTION PAGE]   Error type: {type(attempt_error).__name__}")
                logger.warning(f"[NOTION PAGE]   Error message: {str(attempt_error)[:200]}...")
                
                # Save error for final reporting if this is the last attempt
                create_error = attempt_error
                
                # If this is not the last attempt, continue to next format
                if attempt < len(parent_formats_to_try):
                    logger.info(f"[NOTION PAGE]   Trying next parent format...")
                    continue
                else:
                    # Last attempt failed, log full error
                    logger.error(f"[NOTION PAGE] ✗ All {len(parent_formats_to_try)} attempts failed")
                    logger.error(f"[NOTION PAGE] Final error type: {type(create_error).__name__}")
                    logger.error(f"[NOTION PAGE] Final error message: {str(create_error)}")
                    logger.error(f"[NOTION PAGE] Last parameters used: {create_params}")
                    raise
        
        # Extract page ID from result
        logger.info("[NOTION PAGE] Extracting page information from result...")
        page_id = None
        page_url = None
        
        logger.debug(f"[NOTION PAGE] Attempting to parse result (type: {type(create_result)})...")
        
        # The result might be an array since we created pages in an array
        # Or it might be a single page object/dict
        
        # Handle array result (multiple pages)
        if isinstance(create_result, (list, tuple)):
            logger.debug(f"[NOTION PAGE] Result is an array with {len(create_result)} items")
            if len(create_result) > 0:
                create_result = create_result[0]  # Take first page
                logger.debug(f"[NOTION PAGE] Using first page from array")
            else:
                logger.warning("[NOTION PAGE] Result array is empty!")
                create_result = None
        
        if create_result is None:
            logger.warning("[NOTION PAGE] Result is None, cannot extract page info")
        # Try to parse result (could be dict, string, or object)
        elif isinstance(create_result, dict):
            logger.debug("[NOTION PAGE] Result is a dictionary")
            logger.debug(f"[NOTION PAGE] Dictionary keys: {list(create_result.keys())}")
            
            # Try various possible key names for page ID
            page_id = (create_result.get("id") or 
                      create_result.get("page_id") or 
                      create_result.get("pageId") or
                      create_result.get("object") or
                      None)
            
            # Try various possible key names for page URL
            page_url = (create_result.get("url") or 
                       create_result.get("page_url") or 
                       create_result.get("pageUrl") or
                       create_result.get("public_url") or
                       None)
            
            logger.debug(f"[NOTION PAGE] Extracted from dict - ID: {page_id}, URL: {page_url}")
            
            # If we have a result but no ID, log the full structure for debugging
            if not page_id:
                logger.warning("[NOTION PAGE] Could not find page ID in result dictionary")
                logger.debug(f"[NOTION PAGE] Full result structure: {create_result}")
        elif hasattr(create_result, 'id'):
            logger.debug("[NOTION PAGE] Result is an object with 'id' attribute")
            page_id = create_result.id
            page_url = getattr(create_result, 'url', None) or getattr(create_result, 'page_url', None)
            logger.debug(f"[NOTION PAGE] Extracted from object - ID: {page_id}, URL: {page_url}")
        elif isinstance(create_result, str):
            logger.debug("[NOTION PAGE] Result is a string, attempting to extract ID...")
            # Try to extract ID from string
            import re
            id_match = re.search(r'[a-f0-9]{32}', create_result)
            if id_match:
                page_id = id_match.group(0)
                logger.debug(f"[NOTION PAGE] Extracted ID from string: {page_id}")
            else:
                logger.debug("[NOTION PAGE] No ID pattern found in string")
                logger.debug(f"[NOTION PAGE] Result string: {create_result[:200]}...")
        
        if page_id:
            logger.info(f"[NOTION PAGE] ✓ Page ID extracted: {page_id[:8]}...{page_id[-8:]}")
        else:
            logger.warning("[NOTION PAGE] Could not extract page ID from creation result")
            logger.warning("[NOTION PAGE] This might be normal if the API returns URL directly")
            logger.debug(f"[NOTION PAGE] Full result: {create_result}")
        
        if page_url:
            logger.info(f"[NOTION PAGE] ✓ Page URL extracted: {page_url}")
        else:
            logger.debug("[NOTION PAGE] No page URL found in result, will construct from ID if available")
        
        # Append blocks to page
        if append_tool and page_id:
            logger.info("[NOTION BLOCKS] Appending content blocks to page...")
            logger.info(f"[NOTION BLOCKS] Using tool: '{append_tool.name}'")
            logger.info(f"[NOTION BLOCKS] Page ID: {page_id[:8]}...{page_id[-8:]}")
            logger.info(f"[NOTION BLOCKS] Number of blocks: {len(formatted['blocks'])}")
            
            append_start = time.time()
            
            # Try different parameter formats
            append_params = {
                "page_id": page_id,
                "children": formatted["blocks"]
            }
            
            logger.debug(f"[NOTION BLOCKS] Append parameters: page_id={page_id[:8]}..., children={len(formatted['blocks'])} blocks")
            logger.debug(f"[NOTION BLOCKS] First block type: {formatted['blocks'][0].get('type', 'unknown') if formatted['blocks'] else 'none'}")
            
            try:
                append_result = await append_tool.ainvoke(append_params)
                append_time = time.time() - append_start
                
                logger.info(f"[NOTION BLOCKS] Block append completed in {append_time:.2f}s")
                logger.debug(f"[NOTION BLOCKS] Append result type: {type(append_result)}")
                logger.debug(f"[NOTION BLOCKS] Append result: {append_result}")
            except Exception as append_error:
                append_time = time.time() - append_start
                logger.error(f"[NOTION BLOCKS] Block append failed after {append_time:.2f}s")
                logger.error(f"[NOTION BLOCKS] Error type: {type(append_error).__name__}")
                logger.error(f"[NOTION BLOCKS] Error message: {str(append_error)}")
                logger.error(f"[NOTION BLOCKS] Parameters used: page_id={page_id[:8]}..., blocks={len(formatted['blocks'])}")
                logger.warning("[NOTION BLOCKS] Page may have been created but without content blocks")
        elif not append_tool and page_id:
            logger.warning("[NOTION BLOCKS] No block append tool found!")
            logger.warning("[NOTION BLOCKS] Page was created but we cannot add content blocks")
            logger.warning("[NOTION BLOCKS] Available tools: " + ", ".join([t.name for t in tools]))
        elif not page_id:
            logger.warning("[NOTION BLOCKS] Cannot append blocks: no page ID available")
            logger.warning("[NOTION BLOCKS] Page creation may have failed or returned unexpected format")
        
        # Construct page URL if not provided
        logger.info("[NOTION URL] Constructing page URL...")
        if not page_url and page_id:
            # Notion page URL format: https://www.notion.so/{title}-{page_id}
            # Remove dashes from page_id for URL
            clean_id = page_id.replace('-', '')
            page_url = f"https://www.notion.so/{clean_id}"
            logger.info(f"[NOTION URL] Constructed URL from page ID: {page_url}")
        elif not page_url:
            logger.warning("[NOTION URL] Could not determine page URL")
            logger.warning("[NOTION URL] Page ID was: " + (page_id[:20] + "..." if page_id else "None"))
            logger.warning("[NOTION URL] Result was: " + str(type(create_result)))
        
        total_time = time.time() - save_start_time
        
        logger.info("=" * 80)
        if page_url:
            logger.info("[NOTION] ✓ Notion save completed successfully")
            logger.info(f"[NOTION] Page URL: {page_url}")
            logger.info(f"[NOTION] Page ID: {page_id[:8]}...{page_id[-8:] if page_id else 'N/A'}")
        else:
            logger.warning("[NOTION] ⚠ Notion save completed but no URL available")
            logger.warning("[NOTION] Page may have been created but URL extraction failed")
        
        logger.info(f"[NOTION] Total save time: {total_time:.2f}s")
        logger.info(f"[NOTION] Time breakdown:")
        logger.info(f"[NOTION]   Tool fetch: {tools_time:.2f}s")
        logger.info(f"[NOTION]   Page creation: {create_time:.2f}s")
        if append_tool and page_id:
            logger.info(f"[NOTION]   Block append: {append_time:.2f}s")
        logger.info("=" * 80)
        
        return page_url
        
    except Exception as e:
        total_time = time.time() - save_start_time
        
        # Check if this is an ExceptionGroup (has 'exceptions' attribute)
        is_exception_group = hasattr(e, 'exceptions') and isinstance(e.exceptions, (list, tuple))
        
        logger.error("=" * 80)
        logger.error("[NOTION] ✗ Failed to save summary to Notion")
        logger.error(f"[NOTION] Error after {total_time:.2f}s")
        
        if is_exception_group:
            logger.error(f"[NOTION] Error type: ExceptionGroup ({len(e.exceptions)} sub-exceptions)")
            
            # Extract and log all sub-exceptions
            for i, exc in enumerate(e.exceptions, 1):
                logger.error(f"[NOTION] Sub-exception {i}/{len(e.exceptions)}:")
                logger.error(f"[NOTION]   Type: {type(exc).__name__}")
                logger.error(f"[NOTION]   Message: {str(exc)}")
                
                # Check for HTTP errors
                if hasattr(exc, 'response'):
                    logger.error(f"[NOTION]   HTTP status: {exc.response.status_code if hasattr(exc.response, 'status_code') else 'N/A'}")
                    logger.error(f"[NOTION]   HTTP URL: {exc.response.url if hasattr(exc.response, 'url') else 'N/A'}")
            
            # Check for 401 in any sub-exception
            has_401 = any("401" in str(exc) or "Unauthorized" in str(exc) or 
                         (hasattr(exc, 'response') and hasattr(exc.response, 'status_code') and exc.response.status_code == 401)
                         for exc in e.exceptions)
        else:
            logger.error(f"[NOTION] Error type: {type(e).__name__}")
            logger.error(f"[NOTION] Error message: {str(e)}")
            has_401 = "401" in str(e).lower() or "unauthorized" in str(e).lower()
        
        if has_401:
            logger.error("[NOTION] Authentication error detected (401 Unauthorized)!")
            logger.error("[NOTION] Possible solutions:")
            logger.error("[NOTION]   1. Check NOTION_API_KEY in .env file")
            logger.error("[NOTION]   2. Verify API key is correct for Notion MCP server")
            logger.error("[NOTION]   3. Ensure API key has Notion permissions enabled in Tadata dashboard")
            logger.error("[NOTION]   4. Try regenerating the API key in Tadata dashboard")
            logger.error(f"[NOTION]   5. Current API key source: {'NOTION_API_KEY' if settings.NOTION_API_KEY else 'TADATA_API_KEY (fallback)'}")
            logger.error(f"[NOTION]   6. Current API key length: {len(settings.notion_api_key)} characters")
            logger.error(f"[NOTION]   7. Notion MCP URL: {settings.notion_mcp_url}")
            logger.error(f"[NOTION]   8. Full URL (masked): {settings.notion_full_url.split('=')[0]}=[MASKED]")
        
        # Check for other specific error types
        error_str = str(e).lower()
        if not has_401:
            if "404" in error_str or "not found" in error_str:
                logger.error("[NOTION] Not found error - check Notion MCP server URL")
                logger.error(f"[NOTION] Current URL: {settings.notion_mcp_url}")
            elif "timeout" in error_str:
                logger.error("[NOTION] Timeout error - check network connectivity")
            elif "connection" in error_str:
                logger.error("[NOTION] Connection error - check network and server availability")
        
        logger.error("[NOTION] Full error traceback:")
        logger.exception(e)
        logger.error("=" * 80)
        logger.warning("[NOTION] Continuing without Notion save - summary will still be returned")
        return None
        total_time = time.time() - save_start_time
        logger.error("=" * 80)
        logger.error("[NOTION] ✗ Failed to save summary to Notion")
        logger.error(f"[NOTION] Error after {total_time:.2f}s")
        logger.error(f"[NOTION] Error type: {type(e).__name__}")
        logger.error(f"[NOTION] Error message: {str(e)}")
        
        # Check for specific error types
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            logger.error("[NOTION] Authentication error detected!")
            logger.error("[NOTION] Possible solutions:")
            logger.error("[NOTION]   1. Check NOTION_API_KEY in .env file")
            logger.error("[NOTION]   2. Verify API key is correct for Notion MCP server")
            logger.error("[NOTION]   3. Ensure API key has Notion permissions")
            logger.error("[NOTION]   4. Try regenerating the API key in Tadata dashboard")
            logger.error(f"[NOTION]   5. Current API key source: {'NOTION_API_KEY' if settings.NOTION_API_KEY else 'TADATA_API_KEY (fallback)'}")
            logger.error(f"[NOTION]   6. Current API key length: {len(settings.notion_api_key)} characters")
            logger.error(f"[NOTION]   7. Notion MCP URL: {settings.notion_mcp_url}")
            logger.error(f"[NOTION]   8. Full URL (masked): {settings.notion_full_url.split('=')[0]}=[MASKED]")
        elif "404" in error_str or "not found" in error_str:
            logger.error("[NOTION] Not found error - check Notion MCP server URL")
            logger.error(f"[NOTION] Current URL: {settings.notion_mcp_url}")
        elif "timeout" in error_str:
            logger.error("[NOTION] Timeout error - check network connectivity")
        elif "connection" in error_str:
            logger.error("[NOTION] Connection error - check network and server availability")
        
        logger.error("[NOTION] Full error traceback:")
        logger.exception(e)
        logger.error("=" * 80)
        logger.warning("[NOTION] Continuing without Notion save - summary will still be returned")
        return None

