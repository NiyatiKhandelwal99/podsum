"""Tadata MCP service for YouTube podcast search via Tavily with Gradient AI enhancement."""

import logging
import json
import re
import time
from typing import Optional
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import settings

logger = logging.getLogger(__name__)

# Global MCP client instance
_mcp_client: MultiServerMCPClient | None = None

# Global Gradient client instance
_gradient_client = None


def _get_mcp_client() -> MultiServerMCPClient:
    """Get or create the MCP client singleton."""
    global _mcp_client
    logger.debug("Getting MCP client instance")
    if _mcp_client is None:
        logger.info("Initializing new MCP client")
        logger.debug(f"MCP URL: {settings.tadata_mcp_url}")
        logger.debug(f"Tadata API key present: {bool(settings.tadata_api_key)}")
        _mcp_client = MultiServerMCPClient(
            {
                "tavily": {
                    "transport": "streamable_http",
                    "url": settings.tadata_full_url
                }
            }
        )
        logger.info("MCP client initialized successfully")
    else:
        logger.debug("Reusing existing MCP client instance")
    return _mcp_client


def _get_gradient_client():
    """Get or create the Gradient client singleton."""
    global _gradient_client
    logger.debug("Getting Gradient client instance")
    
    if _gradient_client is None:
        logger.debug(f"Gradient client not initialized. Model access key present: {bool(settings.model_access_key)}")
        if settings.model_access_key:
            logger.info("Initializing Gradient AI client")
            logger.debug(f"Using model: {settings.gradient_model}")
            try:
                from gradient import Gradient
                start_time = time.time()
                _gradient_client = Gradient(model_access_key=settings.model_access_key)
                init_time = time.time() - start_time
                logger.info(f"Gradient AI client initialized successfully in {init_time:.2f}s")
                logger.debug(f"Gradient client type: {type(_gradient_client)}")
            except ImportError as e:
                logger.error(f"Failed to import Gradient library: {e}")
                logger.warning("Gradient AI will not be available")
                _gradient_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Gradient client: {e}", exc_info=True)
                logger.warning("Gradient AI will not be available, falling back to keyword-based methods")
                _gradient_client = None
        else:
            logger.warning("Model access key not configured, Gradient AI unavailable")
            _gradient_client = None
    else:
        logger.debug("Reusing existing Gradient client instance")
    
    if _gradient_client:
        logger.debug("Gradient AI client is available")
    else:
        logger.debug("Gradient AI client is NOT available")
    
    return _gradient_client


async def _enhance_query_with_ai(query: str) -> str:
    """
    Use Gradient AI to intelligently enhance the search query.
    
    Args:
        query: Original user query
        
    Returns:
        Enhanced query optimized for finding full podcast episodes
    """
    logger.info(f"[QUERY ENHANCEMENT] Starting AI query enhancement")
    logger.debug(f"[QUERY ENHANCEMENT] Original query: '{query}'")
    logger.debug(f"[QUERY ENHANCEMENT] Query length: {len(query)} characters")
    
    gradient_client = _get_gradient_client()
    if not gradient_client:
        logger.warning("[QUERY ENHANCEMENT] Gradient AI not available, using keyword-based enhancement")
        return _enhance_query_with_keywords(query)
    
    logger.info("[QUERY ENHANCEMENT] Using Gradient AI for query enhancement")
    logger.debug(f"[QUERY ENHANCEMENT] Model: {settings.gradient_model}")
    
    try:
        prompt = f"""Analyze this podcast search query: "{query}"

Extract:
1. Podcast show name (if mentioned)
2. Guest/person names
3. Topic or theme

Generate an optimized YouTube search query that will find the FULL EPISODE (not clips or highlights).
Focus on: show name + guest + "full episode" or "interview"
Return ONLY the optimized search query, nothing else."""

        logger.debug(f"[QUERY ENHANCEMENT] Prompt length: {len(prompt)} characters")
        logger.debug(f"[QUERY ENHANCEMENT] Sending request to Gradient AI...")
        
        start_time = time.time()
        response = gradient_client.chat.completions.create(
            model=settings.gradient_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        ai_time = time.time() - start_time
        
        logger.info(f"[QUERY ENHANCEMENT] AI response received in {ai_time:.2f}s")
        logger.debug(f"[QUERY ENHANCEMENT] Response object: {type(response)}")
        logger.debug(f"[QUERY ENHANCEMENT] Response choices count: {len(response.choices)}")
        
        enhanced_query = response.choices[0].message.content.strip()
        logger.info(f"[QUERY ENHANCEMENT] AI-enhanced query: '{enhanced_query}'")
        logger.debug(f"[QUERY ENHANCEMENT] Enhanced query length: {len(enhanced_query)} characters")
        logger.debug(f"[QUERY ENHANCEMENT] Query changed: {query != enhanced_query}")
        
        if hasattr(response, 'usage'):
            logger.debug(f"[QUERY ENHANCEMENT] Token usage: {response.usage}")
        
        return enhanced_query
        
    except Exception as e:
        logger.error(f"[QUERY ENHANCEMENT] AI query enhancement failed: {e}", exc_info=True)
        logger.warning("[QUERY ENHANCEMENT] Falling back to keyword-based enhancement")
        return _enhance_query_with_keywords(query)


def _enhance_query_with_keywords(query: str) -> str:
    """
    Enhance query using keyword-based approach (fallback).
    
    Args:
        query: Original user query
        
    Returns:
        Enhanced query
    """
    logger.info("[KEYWORD ENHANCEMENT] Starting keyword-based query enhancement")
    logger.debug(f"[KEYWORD ENHANCEMENT] Original query: '{query}'")
    
    # Add episode-specific keywords
    enhanced = f"{query} full episode interview"
    logger.info(f"[KEYWORD ENHANCEMENT] Keyword-enhanced query: '{enhanced}'")
    logger.debug(f"[KEYWORD ENHANCEMENT] Enhanced query length: {len(enhanced)} characters")
    logger.debug(f"[KEYWORD ENHANCEMENT] Added keywords: 'full episode interview'")
    
    return enhanced


async def _rank_results_with_ai(results: list, original_query: str) -> Optional[dict]:
    """
    Use Gradient AI to rank and select the best result.
    
    Args:
        results: List of search results with url and title
        original_query: Original user query
        
    Returns:
        Best result dict or None if AI ranking fails
    """
    logger.info("[AI RANKING] Starting AI result ranking")
    logger.debug(f"[AI RANKING] Original query: '{original_query}'")
    logger.debug(f"[AI RANKING] Number of results to rank: {len(results)}")
    
    gradient_client = _get_gradient_client()
    if not gradient_client:
        logger.warning("[AI RANKING] Gradient AI not available, cannot use AI ranking")
        return None
    
    if not results:
        logger.warning("[AI RANKING] No results provided for ranking")
        return None
    
    logger.info(f"[AI RANKING] Using Gradient AI to rank {len(results)} results")
    logger.debug(f"[AI RANKING] Model: {settings.gradient_model}")
    
    # Log all results being ranked
    for i, result in enumerate(results, 1):
        logger.debug(f"[AI RANKING] Result {i}: Title='{result.get('title', 'N/A')[:60]}...' URL='{result.get('url', 'N/A')[:60]}...'")
    
    try:
        # Format results for AI
        formatted_results = "\n".join(
            f"{i+1}. Title: {r.get('title', 'N/A')}\n   URL: {r.get('url', 'N/A')}\n"
            for i, r in enumerate(results)
        )
        
        logger.debug(f"[AI RANKING] Formatted results length: {len(formatted_results)} characters")
        
        prompt = f"""User searched for: "{original_query}"

Here are YouTube search results. Identify which one is the BEST MATCH for a FULL PODCAST EPISODE (30+ minutes):

{formatted_results}

Evaluate each result:
- Is it a full episode or a clip/highlight?
- How relevant is it to the user's query?
- Does the title suggest it's a complete interview/episode?

Return the URL of the best match. Format: "BEST_URL: <url>"
If no good match exists, return "NO_MATCH"."""

        logger.debug(f"[AI RANKING] Prompt length: {len(prompt)} characters")
        logger.debug(f"[AI RANKING] Sending ranking request to Gradient AI...")
        
        start_time = time.time()
        response = gradient_client.chat.completions.create(
            model=settings.gradient_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        ai_time = time.time() - start_time
        
        logger.info(f"[AI RANKING] AI response received in {ai_time:.2f}s")
        logger.debug(f"[AI RANKING] Response object: {type(response)}")
        
        ai_response = response.choices[0].message.content.strip()
        logger.info(f"[AI RANKING] AI ranking response: '{ai_response}'")
        logger.debug(f"[AI RANKING] Response length: {len(ai_response)} characters")
        
        if hasattr(response, 'usage'):
            logger.debug(f"[AI RANKING] Token usage: {response.usage}")
        
        # Extract URL from response
        if "BEST_URL:" in ai_response:
            logger.debug("[AI RANKING] Found BEST_URL marker in response")
            url_match = re.search(r'BEST_URL:\s*(https?://[^\s]+)', ai_response)
            if url_match:
                best_url = url_match.group(1)
                logger.info(f"[AI RANKING] Extracted best URL: '{best_url}'")
                
                # Find the result with this URL
                logger.debug("[AI RANKING] Searching for matching result...")
                for i, result in enumerate(results, 1):
                    result_url = result.get('url', '')
                    logger.debug(f"[AI RANKING] Comparing result {i}: '{result_url[:60]}...' with '{best_url[:60]}...'")
                    
                    if result_url == best_url or best_url in result_url:
                        logger.info(f"[AI RANKING] Match found at index {i-1}")
                        logger.info(f"[AI RANKING] AI selected: '{result.get('title', 'N/A')}'")
                        logger.debug(f"[AI RANKING] Selected URL: '{result_url}'")
                        return result
                
                logger.warning(f"[AI RANKING] Extracted URL '{best_url}' not found in results list")
            else:
                logger.warning("[AI RANKING] Could not extract URL from BEST_URL marker")
        elif "NO_MATCH" in ai_response:
            logger.warning("[AI RANKING] AI indicated no good match found")
        else:
            logger.warning(f"[AI RANKING] Unexpected response format: '{ai_response[:100]}...'")
        
        logger.warning("[AI RANKING] AI did not return a valid best URL, ranking failed")
        return None
        
    except Exception as e:
        logger.error(f"[AI RANKING] AI result ranking failed: {e}", exc_info=True)
        logger.warning("[AI RANKING] Falling back to keyword-based ranking")
        return None


def _rank_results_with_keywords(results: list) -> Optional[dict]:
    """
    Rank results using keyword-based scoring (fallback).
    
    Args:
        results: List of search results
        
    Returns:
        Best ranked result
    """
    logger.info("[KEYWORD RANKING] Starting keyword-based result ranking")
    logger.debug(f"[KEYWORD RANKING] Number of results to rank: {len(results)}")
    
    if not results:
        logger.warning("[KEYWORD RANKING] No results provided for ranking")
        return None
    
    positive_keywords = ["episode", "interview", "full", "hour", "hours", "podcast", "ep"]
    negative_keywords = ["clip", "short", "highlights", "trailer", "teaser", "preview", "best moments"]
    
    logger.debug(f"[KEYWORD RANKING] Positive keywords: {positive_keywords}")
    logger.debug(f"[KEYWORD RANKING] Negative keywords: {negative_keywords}")
    logger.debug(f"[KEYWORD RANKING] Scoring each result...")
    
    scored_results = []
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "").lower()
        url = result.get("url", "").lower()
        combined_text = f"{title} {url}"
        
        logger.debug(f"[KEYWORD RANKING] Result {i}: Title='{title[:50]}...'")
        
        score = 0
        positive_matches = []
        negative_matches = []
        
        # Positive keywords
        for keyword in positive_keywords:
            if keyword in combined_text:
                score += 2
                positive_matches.append(keyword)
        
        # Negative keywords
        for keyword in negative_keywords:
            if keyword in combined_text:
                score -= 3
                negative_matches.append(keyword)
        
        scored_results.append({
            "result": result,
            "score": score
        })
        
        logger.info(f"[KEYWORD RANKING] Result {i} scored: {score} points")
        logger.debug(f"[KEYWORD RANKING]   Title: '{result.get('title', 'N/A')[:60]}...'")
        logger.debug(f"[KEYWORD RANKING]   Positive matches: {positive_matches}")
        logger.debug(f"[KEYWORD RANKING]   Negative matches: {negative_matches}")
        logger.debug(f"[KEYWORD RANKING]   Final score: {score}")
    
    # Sort by score (highest first)
    logger.debug("[KEYWORD RANKING] Sorting results by score...")
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Log sorted results
    logger.info("[KEYWORD RANKING] Ranked results:")
    for i, scored in enumerate(scored_results[:5], 1):  # Log top 5
        logger.info(f"[KEYWORD RANKING]   {i}. Score: {scored['score']}, Title: '{scored['result'].get('title', 'N/A')[:50]}...'")
    
    if scored_results and scored_results[0]["score"] > 0:
        best = scored_results[0]["result"]
        best_score = scored_results[0]["score"]
        logger.info(f"[KEYWORD RANKING] Selected best result with score: {best_score}")
        logger.info(f"[KEYWORD RANKING] Selected title: '{best.get('title', 'N/A')}'")
        logger.debug(f"[KEYWORD RANKING] Selected URL: '{best.get('url', 'N/A')}'")
        return best
    
    # If all scores are negative or zero, return first result
    if results:
        logger.warning("[KEYWORD RANKING] All scores are negative or zero")
        logger.info("[KEYWORD RANKING] Returning first result as fallback")
        logger.debug(f"[KEYWORD RANKING] Fallback result title: '{results[0].get('title', 'N/A')}'")
        return results[0]
    
    logger.warning("[KEYWORD RANKING] No results to return")
    return None


def _parse_tavily_results(result) -> list:
    """
    Parse Tavily search results into a list of result dicts.
    
    Args:
        result: Raw result from Tavily tool
        
    Returns:
        List of result dicts with url and title
    """
    logger.debug("[PARSE RESULTS] Starting Tavily result parsing")
    logger.debug(f"[PARSE RESULTS] Result type: {type(result)}")
    
    results_list = []
    
    # Convert result to string if needed
    if hasattr(result, 'content'):
        text_content = result.content
        logger.debug(f"[PARSE RESULTS] Using result.content, type: {type(text_content)}")
    elif isinstance(result, str):
        text_content = result
        logger.debug(f"[PARSE RESULTS] Result is string, length: {len(text_content)}")
    else:
        text_content = str(result)
        logger.debug(f"[PARSE RESULTS] Converted result to string, length: {len(text_content)}")
    
    logger.debug(f"[PARSE RESULTS] Text content preview: {text_content[:200]}...")
    
    # Try to parse as JSON
    try:
        if isinstance(text_content, str) and (text_content.strip().startswith('{') or text_content.strip().startswith('[')):
            logger.debug("[PARSE RESULTS] Attempting JSON parsing...")
            parsed = json.loads(text_content)
            logger.debug(f"[PARSE RESULTS] JSON parsed successfully, type: {type(parsed)}")
            
            # Handle array of results
            if isinstance(parsed, list):
                results_list = parsed
                logger.debug(f"[PARSE RESULTS] Parsed as list with {len(results_list)} items")
            elif isinstance(parsed, dict):
                results_list = parsed.get("results", [])
                logger.debug(f"[PARSE RESULTS] Parsed as dict, extracted {len(results_list)} results")
            else:
                logger.warning(f"[PARSE RESULTS] Unexpected parsed type: {type(parsed)}")
                
    except json.JSONDecodeError as e:
        logger.warning(f"[PARSE RESULTS] JSON parsing failed: {e}")
        logger.debug("[PARSE RESULTS] Will try regex extraction")
    except TypeError as e:
        logger.warning(f"[PARSE RESULTS] Type error during parsing: {e}")
    except Exception as e:
        logger.error(f"[PARSE RESULTS] Unexpected error during parsing: {e}", exc_info=True)
    
    # Extract YouTube URLs from results
    logger.debug(f"[PARSE RESULTS] Processing {len(results_list)} items for YouTube URLs...")
    youtube_results = []
    
    for i, item in enumerate(results_list, 1):
        if isinstance(item, dict):
            url = item.get("url", "")
            title = item.get("title", "")
            logger.debug(f"[PARSE RESULTS] Item {i}: URL='{url[:50]}...' Title='{title[:50]}...'")
            
            if "youtube.com" in url or "youtu.be" in url:
                youtube_results.append({
                    "url": url,
                    "title": item.get("title", ""),
                    "description": item.get("content", item.get("description", ""))
                })
                logger.debug(f"[PARSE RESULTS] Added YouTube result {len(youtube_results)}: '{title[:50]}...'")
            else:
                logger.debug(f"[PARSE RESULTS] Item {i} is not a YouTube URL, skipping")
        else:
            logger.debug(f"[PARSE RESULTS] Item {i} is not a dict (type: {type(item)}), skipping")
    
    logger.info(f"[PARSE RESULTS] Found {len(youtube_results)} YouTube results from structured data")
    
    # Fallback: regex extraction from text
    if not youtube_results:
        logger.warning("[PARSE RESULTS] No YouTube results from structured parsing, trying regex extraction")
        youtube_patterns = [
            r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)',
            r'(https?://youtu\.be/[\w-]+)',
            r'(https?://(?:www\.)?youtube\.com/embed/[\w-]+)',
        ]
        
        logger.debug(f"[PARSE RESULTS] Trying {len(youtube_patterns)} regex patterns...")
        for pattern_idx, pattern in enumerate(youtube_patterns, 1):
            logger.debug(f"[PARSE RESULTS] Pattern {pattern_idx}: {pattern}")
            matches = list(re.finditer(pattern, text_content))
            logger.debug(f"[PARSE RESULTS] Pattern {pattern_idx} found {len(matches)} matches")
            
            for match_idx, match in enumerate(matches, 1):
                url = match.group(1)
                logger.debug(f"[PARSE RESULTS] Match {match_idx}: '{url}'")
                youtube_results.append({
                    "url": url,
                    "title": "",
                    "description": ""
                })
        
        logger.info(f"[PARSE RESULTS] Regex extraction found {len(youtube_results)} YouTube URLs")
    
    logger.info(f"[PARSE RESULTS] Total YouTube results parsed: {len(youtube_results)}")
    
    # Log all parsed results
    for i, result in enumerate(youtube_results, 1):
        logger.debug(f"[PARSE RESULTS] Parsed result {i}: URL='{result['url'][:60]}...' Title='{result['title'][:50]}...'")
    
    return youtube_results


async def search_youtube_podcast(query: str) -> dict:
    """
    Search for a YouTube podcast using Tavily via Tadata MCP with AI enhancement.
    
    Args:
        query: Natural language search query (e.g., "Joe Rogan podcast with Elon Musk")
        
    Returns:
        dict with youtube_url and title
        
    Raises:
        Exception: If search fails or no YouTube results found
    """
    search_start_time = time.time()
    logger.info("=" * 80)
    logger.info(f"[SEARCH] Starting YouTube podcast search")
    logger.info(f"[SEARCH] Query: '{query}'")
    logger.info(f"[SEARCH] Query length: {len(query)} characters")
    logger.debug(f"[SEARCH] Timestamp: {time.time()}")
    
    # Step 1: Enhance query with AI (or fallback to keywords)
    logger.info("[SEARCH] Step 1: Query enhancement")
    enhance_start = time.time()
    enhanced_query = await _enhance_query_with_ai(query)
    enhance_time = time.time() - enhance_start
    logger.info(f"[SEARCH] Query enhancement completed in {enhance_time:.2f}s")
    logger.info(f"[SEARCH] Enhanced query: '{enhanced_query}'")
    logger.debug(f"[SEARCH] Enhancement method: {'AI' if enhanced_query != f'{query} full episode interview' else 'Keyword-based'}")
    
    # Step 2: Search Tavily with advanced parameters
    logger.info("[SEARCH] Step 2: Tavily search")
    tavily_start = time.time()
    
    logger.debug("[SEARCH] Getting MCP client...")
    client = _get_mcp_client()
    logger.debug("[SEARCH] MCP client obtained")
    
    # Get available tools from MCP
    logger.debug("[SEARCH] Fetching available tools from MCP...")
    tools = await client.get_tools()
    logger.info(f"[SEARCH] Found {len(tools)} available MCP tools")
    logger.debug(f"[SEARCH] Available MCP tools: {[t.name for t in tools]}")
    
    # Find the Tavily search tool
    logger.debug("[SEARCH] Searching for Tavily search tool...")
    tavily_tool = None
    for tool in tools:
        tool_name_lower = tool.name.lower()
        logger.debug(f"[SEARCH] Checking tool: '{tool.name}'")
        if "search" in tool_name_lower or "tavily" in tool_name_lower:
            tavily_tool = tool
            logger.info(f"[SEARCH] Found Tavily tool: '{tool.name}'")
            break
    
    if not tavily_tool:
        logger.error("[SEARCH] Tavily search tool not found in MCP server")
        logger.error(f"[SEARCH] Available tools were: {[t.name for t in tools]}")
        raise Exception("Tavily search tool not found in MCP server")
    
    logger.info(f"[SEARCH] Using tool: '{tavily_tool.name}'")
    logger.debug(f"[SEARCH] Tool type: {type(tavily_tool)}")
    
    # Invoke the search tool with advanced parameters
    search_params = {
        "query": enhanced_query,
        "max_results": 10,
        "search_depth": "advanced"
    }
    
    logger.info(f"[SEARCH] Invoking Tavily search with parameters:")
    logger.info(f"[SEARCH]   Query: '{search_params['query']}'")
    logger.info(f"[SEARCH]   Max results: {search_params['max_results']}")
    logger.info(f"[SEARCH]   Search depth: {search_params['search_depth']}")
    
    logger.debug("[SEARCH] Calling tavily_tool.ainvoke()...")
    result = await tavily_tool.ainvoke(search_params)
    tavily_time = time.time() - tavily_start
    logger.info(f"[SEARCH] Tavily search completed in {tavily_time:.2f}s")
    logger.debug(f"[SEARCH] Tavily result type: {type(result)}")
    logger.debug(f"[SEARCH] Tavily result preview: {str(result)[:500]}...")
    
    # Step 3: Parse all results
    logger.info("[SEARCH] Step 3: Parse results")
    parse_start = time.time()
    all_results = _parse_tavily_results(result)
    parse_time = time.time() - parse_start
    logger.info(f"[SEARCH] Result parsing completed in {parse_time:.2f}s")
    logger.info(f"[SEARCH] Found {len(all_results)} YouTube results")
    
    if not all_results:
        logger.error("[SEARCH] No YouTube results found after parsing")
        logger.error(f"[SEARCH] Original query: '{query}'")
        logger.error(f"[SEARCH] Enhanced query: '{enhanced_query}'")
        raise Exception(f"No YouTube podcast found for: {query}")
    
    # Log all results
    logger.info("[SEARCH] All parsed results:")
    for i, result_item in enumerate(all_results, 1):
        logger.info(f"[SEARCH]   {i}. {result_item.get('title', 'N/A')[:60]}...")
        logger.debug(f"[SEARCH]      URL: {result_item.get('url', 'N/A')[:60]}...")
    
    # Step 4: Rank results with AI (or fallback to keywords)
    logger.info("[SEARCH] Step 4: Rank results")
    rank_start = time.time()
    
    logger.debug("[SEARCH] Attempting AI ranking...")
    best_result = await _rank_results_with_ai(all_results, query)
    
    if best_result:
        logger.info("[SEARCH] AI ranking succeeded")
        logger.debug(f"[SEARCH] AI selected result: '{best_result.get('title', 'N/A')}'")
    else:
        logger.info("[SEARCH] AI ranking unavailable or failed, using keyword-based ranking")
        best_result = _rank_results_with_keywords(all_results)
    
    rank_time = time.time() - rank_start
    logger.info(f"[SEARCH] Result ranking completed in {rank_time:.2f}s")
    
    if not best_result:
        logger.error("[SEARCH] No valid result found after ranking")
        logger.error(f"[SEARCH] Had {len(all_results)} results to choose from")
        raise Exception(f"No suitable YouTube podcast found for: {query}")
    
    youtube_url = best_result.get("url")
    title = best_result.get("title", "")
    
    total_time = time.time() - search_start_time
    
    logger.info("=" * 80)
    logger.info("[SEARCH] Search completed successfully")
    logger.info(f"[SEARCH] Selected YouTube URL: {youtube_url}")
    logger.info(f"[SEARCH] Selected title: '{title}'")
    logger.info(f"[SEARCH] Total search time: {total_time:.2f}s")
    logger.info(f"[SEARCH] Time breakdown:")
    logger.info(f"[SEARCH]   Query enhancement: {enhance_time:.2f}s ({enhance_time/total_time*100:.1f}%)")
    logger.info(f"[SEARCH]   Tavily search: {tavily_time:.2f}s ({tavily_time/total_time*100:.1f}%)")
    logger.info(f"[SEARCH]   Result parsing: {parse_time:.2f}s ({parse_time/total_time*100:.1f}%)")
    logger.info(f"[SEARCH]   Result ranking: {rank_time:.2f}s ({rank_time/total_time*100:.1f}%)")
    logger.info("=" * 80)
    
    return {
        "youtube_url": youtube_url,
        "title": title
    }


def _extract_youtube_result(result) -> tuple[str | None, str]:
    """
    Extract YouTube URL and title from Tavily search results.
    (Legacy function kept for backward compatibility)
    
    Args:
        result: Result from Tavily search tool
        
    Returns:
        Tuple of (youtube_url, title)
    """
    logger.debug("[LEGACY EXTRACT] Using legacy extraction function")
    results = _parse_tavily_results(result)
    if results:
        logger.debug(f"[LEGACY EXTRACT] Found {len(results)} results, returning first")
        return results[0].get("url"), results[0].get("title", "")
    logger.warning("[LEGACY EXTRACT] No results found")
    return None, ""
