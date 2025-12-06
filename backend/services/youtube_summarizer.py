"""YouTube video transcript extraction and summarization service."""

import re
import json
import asyncio
import logging
import tempfile
from typing import Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yt_dlp
from gradient import Gradient

logger = logging.getLogger(__name__)

# Thread pool for parallel API calls
_executor = ThreadPoolExecutor(max_workers=10)

# Semaphore to limit concurrent Gradient API calls (avoid rate limiting)
_api_semaphore = None

def _get_api_semaphore(max_concurrent: int = 3):
    """Get or create semaphore for rate limiting API calls."""
    global _api_semaphore
    if _api_semaphore is None:
        _api_semaphore = asyncio.Semaphore(max_concurrent)
    return _api_semaphore


@dataclass
class VideoSummary:
    """Result of video summarization."""
    video_id: str
    video_url: str
    title: str
    transcript_length: int
    summary: str
    top_learnings: list[str]
    duration_minutes: float


class YouTubeSummarizer:
    """Extracts transcripts from YouTube videos and generates AI summaries."""

    # Chunk size for processing long transcripts (in characters)
    # With 131k token context, we can use MUCH larger chunks
    # 100k chars ≈ 25k tokens, leaving room for prompt + response
    CHUNK_SIZE = 100000  # ~25k tokens per chunk - leverage the large context window
    MAX_CHUNKS_FOR_SUMMARY = 6  # Most videos will only need 1-3 chunks now

    def __init__(self, model_access_key: str, model: str = "openai-gpt-oss-120b", proxy: str = "", cookies_from_browser: str = ""):
        """
        Initialize the summarizer.
        
        Args:
            model_access_key: Gradient AI model access key
            model: Model to use (default: openai-gpt-oss-120b)
            proxy: Optional proxy URL for YouTube requests (e.g., "http://host:port")
            cookies_from_browser: Browser name to extract cookies from (chrome, firefox, safari, etc.)
        """
        self.client = Gradient(model_access_key=model_access_key)
        self.model = model
        self.proxy = proxy
        self.cookies_from_browser = cookies_from_browser

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract the video ID from various YouTube URL formats.
        
        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$',  # Just the video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None

    def get_video_info(self, video_url: str) -> tuple[str, str, float]:
        """
        Fetch video info and transcript using yt-dlp.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Tuple of (transcript text, video title, duration in minutes)
            
        Raises:
            ValueError: If transcript cannot be retrieved
        """
        video_id = self.extract_video_id(video_url)
        
        # Configure yt-dlp options
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB'],
            'subtitlesformat': 'json3',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        # Add proxy if configured
        if self.proxy:
            logger.info("Using proxy for YouTube requests")
            ydl_opts['proxy'] = self.proxy
        
        # Add browser cookies if configured (bypasses bot verification)
        if self.cookies_from_browser:
            logger.info(f"Using cookies from browser: {self.cookies_from_browser}")
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Extracting video info for: {video_url}")
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    raise ValueError(f"Could not extract video info for: {video_url}")
                
                # Get video metadata
                title = info.get('title', f'Video {video_id}')
                duration_seconds = info.get('duration', 0) or 0
                duration_minutes = duration_seconds / 60
                
                logger.info(f"Video: {title} ({duration_minutes:.1f} min)")
                
                # Try to get subtitles
                transcript_text = self._extract_subtitles(info, video_url, ydl)
                
                if not transcript_text:
                    raise ValueError(
                        f"No transcript/subtitles available for video: {title}\n"
                        f"This video may not have captions enabled."
                    )
                
                logger.info(f"Retrieved transcript: {len(transcript_text)} chars")
                return transcript_text, title, duration_minutes
                
        except yt_dlp.utils.DownloadError as e:
            error_str = str(e)
            if "Private video" in error_str:
                raise ValueError("This video is private and cannot be accessed.")
            elif "Video unavailable" in error_str:
                raise ValueError("This video is unavailable.")
            elif "Sign in" in error_str or "bot" in error_str.lower():
                raise ValueError(
                    "YouTube requires bot verification. To fix this:\n\n"
                    "1. Add to your .env file:\n"
                    "   YOUTUBE_COOKIES_FROM_BROWSER=chrome\n"
                    "   (or: firefox, safari, edge, brave)\n\n"
                    "2. Make sure you're logged into YouTube in that browser\n\n"
                    "3. Restart the server and try again"
                )
            else:
                raise ValueError(f"Failed to access video: {e}")
        except Exception as e:
            raise ValueError(f"Failed to get video info: {e}")

    def _extract_subtitles(self, info: dict, video_url: str, ydl: yt_dlp.YoutubeDL) -> Optional[str]:
        """Extract subtitles from video info or download them."""
        
        # Check for available subtitles
        subtitles = info.get('subtitles', {})
        automatic_captions = info.get('automatic_captions', {})
        
        # Prefer manual subtitles, fall back to auto-generated
        available_subs = subtitles if subtitles else automatic_captions
        
        if not available_subs:
            logger.warning("No subtitles available for this video")
            return None
        
        # Find English subtitles
        sub_lang = None
        for lang in ['en', 'en-US', 'en-GB', 'en-AU']:
            if lang in available_subs:
                sub_lang = lang
                break
        
        # If no English, try first available language
        if not sub_lang and available_subs:
            sub_lang = list(available_subs.keys())[0]
            logger.info(f"No English subtitles, using: {sub_lang}")
        
        if not sub_lang:
            return None
        
        # Get the subtitle URL (prefer json3 format for easier parsing)
        sub_formats = available_subs[sub_lang]
        sub_url = None
        
        for fmt in sub_formats:
            if fmt.get('ext') == 'json3':
                sub_url = fmt.get('url')
                break
        
        # Fall back to first available format
        if not sub_url and sub_formats:
            sub_url = sub_formats[0].get('url')
        
        if not sub_url:
            return None
        
        # Download and parse subtitles
        try:
            import urllib.request
            with urllib.request.urlopen(sub_url, timeout=30) as response:
                sub_data = response.read().decode('utf-8')
            
            # Try to parse as JSON3 format
            try:
                sub_json = json.loads(sub_data)
                events = sub_json.get('events', [])
                
                texts = []
                for event in events:
                    segs = event.get('segs', [])
                    for seg in segs:
                        text = seg.get('utf8', '').strip()
                        if text and text != '\n':
                            texts.append(text)
                
                return ' '.join(texts)
            except json.JSONDecodeError:
                # Not JSON, might be VTT or SRT format
                # Simple extraction: remove timing lines
                lines = sub_data.split('\n')
                texts = []
                for line in lines:
                    line = line.strip()
                    # Skip timing lines, headers, and empty lines
                    if not line or '-->' in line or line.startswith('WEBVTT') or line.isdigit():
                        continue
                    # Remove HTML tags
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    if clean_line:
                        texts.append(clean_line)
                
                return ' '.join(texts)
                
        except Exception as e:
            logger.error(f"Failed to download subtitles: {e}")
            return None

    def _chunk_transcript(self, transcript: str) -> list[str]:
        """
        Split a long transcript into manageable chunks.
        
        Tries to split at sentence boundaries for better context.
        """
        if len(transcript) <= self.CHUNK_SIZE:
            return [transcript]

        chunks = []
        current_pos = 0
        
        while current_pos < len(transcript):
            # Find the end position for this chunk
            end_pos = min(current_pos + self.CHUNK_SIZE, len(transcript))
            
            # If not at the end, try to break at a sentence boundary
            if end_pos < len(transcript):
                # Look for sentence endings in the last 500 chars
                search_start = max(end_pos - 500, current_pos)
                chunk_text = transcript[current_pos:end_pos]
                
                # Find the last sentence ending
                for punct in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                    last_idx = chunk_text.rfind(punct)
                    if last_idx > len(chunk_text) - 500 and last_idx > 0:
                        end_pos = current_pos + last_idx + len(punct)
                        break
            
            chunks.append(transcript[current_pos:end_pos].strip())
            current_pos = end_pos
            
            # Safety limit
            if len(chunks) >= self.MAX_CHUNKS_FOR_SUMMARY:
                logger.warning(f"Transcript too long, truncating at {len(chunks)} chunks")
                break

        logger.info(f"Split transcript into {len(chunks)} chunks")
        return chunks

    def _summarize_chunk(self, chunk: str, chunk_num: int, total_chunks: int) -> str:
        """Summarize a single chunk of transcript."""
        prompt = f"""Summarize the following transcript excerpt (part {chunk_num} of {total_chunks}).

TRANSCRIPT:
\"\"\"
{chunk}
\"\"\"

Provide a concise but comprehensive summary (500-800 words) covering:
- Main topics and themes discussed
- Key insights and notable points
- Important quotes or ideas

Be specific and reference actual content."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500  # Reduced for faster response
        )
        
        # Get response details
        choice = response.choices[0]
        finish_reason = getattr(choice, 'finish_reason', 'unknown')
        summary = choice.message.content or ""
        
        logger.info(f"Chunk {chunk_num}: finish_reason={finish_reason}, length={len(summary)} chars")
        
        # If we hit token limit and got empty response, try a shorter request
        if finish_reason == 'length' and not summary:
            logger.warning(f"Chunk {chunk_num} hit token limit with no output, retrying with shorter prompt")
            # Truncate the chunk and retry with simpler prompt
            truncated_chunk = chunk[:4000]  # Use only first half
            retry_prompt = f"Summarize this transcript in 3-5 bullet points:\n\n{truncated_chunk}"
            
            retry_response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": retry_prompt}],
                max_tokens=1000
            )
            summary = retry_response.choices[0].message.content or ""
            logger.info(f"Chunk {chunk_num} retry: {len(summary)} chars")
        
        if not summary:
            logger.warning(f"Chunk {chunk_num} returned empty summary!")
            summary = f"[Section {chunk_num}: Content could not be summarized]"
        
        return summary

    def _generate_final_summary(self, chunk_summaries: list[str]) -> tuple[str, list[str]]:
        """
        Generate the final summary and top 5 learnings from chunk summaries.
        
        Returns:
            Tuple of (overall summary, list of top 5 learnings)
        """
        # Log combined summaries for debugging
        logger.info(f"Combining {len(chunk_summaries)} chunk summaries")
        for i, s in enumerate(chunk_summaries):
            logger.info(f"  Chunk {i+1} summary: {len(s)} chars")
        
        combined_summaries = "\n\n---\n\n".join(
            f"SECTION {i+1}:\n{summary}" 
            for i, summary in enumerate(chunk_summaries)
        )
        
        logger.info(f"Total combined summaries length: {len(combined_summaries)} chars")

        prompt = f"""I have summarized a long video transcript in sections. Based on these section summaries below, please create:

1. An overall summary (2-3 paragraphs) covering the main themes
2. The TOP 5 most important learnings or takeaways

HERE ARE THE SECTION SUMMARIES:

{combined_summaries}

---

Now provide your response in this exact format:

## SUMMARY
[Write your comprehensive summary here]

## TOP 5 LEARNINGS
1. [First key learning]
2. [Second key learning]
3. [Third key learning]
4. [Fourth key learning]
5. [Fifth key learning]"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500
        )
        
        content = response.choices[0].message.content
        
        # Parse the response
        summary = ""
        learnings = []
        
        # Extract summary
        if "## SUMMARY" in content:
            summary_start = content.find("## SUMMARY") + len("## SUMMARY")
            summary_end = content.find("## TOP 5 LEARNINGS") if "## TOP 5 LEARNINGS" in content else len(content)
            summary = content[summary_start:summary_end].strip()
        
        # Extract learnings
        if "## TOP 5 LEARNINGS" in content:
            learnings_text = content[content.find("## TOP 5 LEARNINGS") + len("## TOP 5 LEARNINGS"):]
            # Parse numbered items
            lines = learnings_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    # Remove the number prefix
                    learning = re.sub(r'^\d+\.\s*', '', line)
                    if learning:
                        learnings.append(learning)
        
        # Fallback if parsing failed
        if not summary:
            summary = content
        if not learnings or len(learnings) < 5:
            learnings = [
                "Unable to parse learnings - please review the summary above",
                "The video contains valuable content worth watching",
                "Consider re-running the summarization",
                "Check the full transcript for details",
                "Manual review recommended"
            ]

        return summary, learnings[:5]

    async def _summarize_chunk_async(self, chunk: str, chunk_num: int, total_chunks: int) -> tuple[int, str]:
        """Async wrapper to run chunk summarization in thread pool with rate limiting."""
        # Use semaphore to limit to 1 concurrent call (Gradient has strict rate limits)
        semaphore = _get_api_semaphore(max_concurrent=1)
        
        async with semaphore:
            # Wait 3 seconds BEFORE making request to respect rate limits
            if chunk_num > 1:
                logger.info(f"Waiting 3s before chunk {chunk_num}...")
                await asyncio.sleep(3)
            
            logger.info(f"Chunk {chunk_num}/{total_chunks}: processing ({len(chunk):,} chars)...")
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(
                _executor,
                self._summarize_chunk,
                chunk,
                chunk_num,
                total_chunks
            )
        
        return chunk_num, summary

    async def summarize_video(self, url: str) -> VideoSummary:
        """
        Main entry point: Extract transcript and generate summary with top learnings.
        
        Args:
            url: YouTube video URL
            
        Returns:
            VideoSummary with all extracted information
        """
        # Extract video ID
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")
        
        logger.info(f"Processing video: {video_id}")
        
        # Get transcript and video info using yt-dlp
        transcript, video_title, duration_minutes = self.get_video_info(url)
        
        # Chunk the transcript for long videos
        chunks = self._chunk_transcript(transcript)
        
        # Summarize chunks sequentially (Gradient has strict rate limits)
        logger.info(f"Summarizing {len(chunks)} chunks sequentially...")
        
        # Create async tasks for all chunks
        tasks = [
            self._summarize_chunk_async(chunk, i+1, len(chunks))
            for i, chunk in enumerate(chunks)
        ]
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Sort by chunk number and extract summaries
        results.sort(key=lambda x: x[0])
        chunk_summaries = [summary for _, summary in results]
        
        logger.info(f"All {len(chunks)} chunks processed")
        
        # Generate final summary and top learnings (with rate limit protection)
        logger.info("Waiting 3s before final summary...")
        await asyncio.sleep(3)
        logger.info("Generating final summary and learnings...")
        semaphore = _get_api_semaphore(max_concurrent=1)
        async with semaphore:
            loop = asyncio.get_event_loop()
            final_summary, top_learnings = await loop.run_in_executor(
                _executor,
                self._generate_final_summary,
                chunk_summaries
            )
        
        return VideoSummary(
            video_id=video_id,
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            title=video_title,
            transcript_length=len(transcript),
            summary=final_summary,
            top_learnings=top_learnings,
            duration_minutes=duration_minutes
        )

