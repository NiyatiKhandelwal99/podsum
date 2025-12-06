"""Utility functions for Gradient API calls with rate limiting and retry logic."""

import asyncio
import logging
import time
from typing import Callable, TypeVar, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def is_rate_limit_error(exception: Exception) -> bool:
    """
    Detect if an exception is a rate limit error.
    
    Checks for:
    - HTTP 429 status codes
    - "rate limit" in error messages
    - Gradient-specific rate limit errors
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()
    
    # Check for rate limit keywords
    rate_limit_keywords = [
        "rate limit",
        "rate_limit",
        "too many requests",
        "429",
        "quota exceeded",
        "throttle",
    ]
    
    if any(keyword in error_str for keyword in rate_limit_keywords):
        return True
    
    # Check for HTTP 429 status code
    if hasattr(exception, 'status_code') and exception.status_code == 429:
        return True
    
    if hasattr(exception, 'response'):
        response = exception.response
        if hasattr(response, 'status_code') and response.status_code == 429:
            return True
    
    return False


async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 5.0,
    backoff_multiplier: float = 2.0,
    operation_name: str = "API call"
) -> T:
    """
    Retry a function with exponential backoff on rate limit errors.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 5.0)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        operation_name: Name of the operation for logging
        
    Returns:
        Result of the function call
        
    Raises:
        Exception: The last exception if all retries are exhausted
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except Exception as e:
            last_exception = e
            
            # Only retry on rate limit errors
            if not is_rate_limit_error(e):
                logger.error(f"[{operation_name}] Non-rate-limit error: {e}")
                raise
            
            # If this was the last attempt, don't wait
            if attempt < max_retries:
                delay = initial_delay * (backoff_multiplier ** attempt)
                logger.warning(
                    f"[{operation_name}] Rate limit error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"[{operation_name}] Rate limit error after {max_retries + 1} attempts. "
                    f"Last error: {e}"
                )
    
    # All retries exhausted
    raise last_exception


def safe_gradient_call(
    gradient_client,
    model: str,
    messages: list[dict],
    max_tokens: int = 2000,
    max_retries: int = 3,
    operation_name: str = "Gradient API call"
):
    """
    Make a safe Gradient API call with automatic retry logic.
    
    Args:
        gradient_client: Gradient client instance
        model: Model name to use
        messages: List of message dicts for the API call
        max_tokens: Maximum tokens for the response
        max_retries: Maximum retry attempts (default: 3)
        operation_name: Name of operation for logging
        
    Returns:
        API response object
        
    Raises:
        Exception: If all retries are exhausted
    """
    def _make_call():
        return gradient_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )
    
    # For sync calls, we need to handle retries synchronously
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return _make_call()
        except Exception as e:
            last_exception = e
            
            # Only retry on rate limit errors
            if not is_rate_limit_error(e):
                logger.error(f"[{operation_name}] Non-rate-limit error: {e}")
                raise
            
            # If this was the last attempt, don't wait
            if attempt < max_retries:
                delay = 5.0 * (2.0 ** attempt)  # 5s, 10s, 20s
                logger.warning(
                    f"[{operation_name}] Rate limit error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"[{operation_name}] Rate limit error after {max_retries + 1} attempts. "
                    f"Last error: {e}"
                )
    
    # All retries exhausted
    raise last_exception

