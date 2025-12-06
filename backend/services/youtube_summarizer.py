"""YouTube video transcript extraction and summarization service."""

import re
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from gradient import Gradient

logger = logging.getLogger(__name__)

# Thread pool for parallel API calls
_executor = ThreadPoolExecutor(max_workers=10)


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
    # Reduced to avoid hitting token limits on the model
    CHUNK_SIZE = 8000  # ~2000 tokens per chunk - smaller for better summaries
    MAX_CHUNKS_FOR_SUMMARY = 30  # Increased limit for longer videos

    def __init__(self, model_access_key: str, model: str = "openai-gpt-oss-120b"):
        """
        Initialize the summarizer.
        
        Args:
            model_access_key: Gradient AI model access key
            model: Model to use (default: openai-gpt-oss-120b)
        """
        self.client = Gradient(model_access_key=model_access_key)
        self.model = model

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

    def get_transcript(self, video_id: str) -> tuple[str, float]:
        """
        Fetch the transcript for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Tuple of (full transcript text, duration in minutes)
            
        Raises:
            ValueError: If transcript cannot be retrieved
        """
        ytt_api = YouTubeTranscriptApi()
        
        try:
            transcript = ytt_api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
        except TranscriptsDisabled:
            raise ValueError(f"Transcripts are disabled for video: {video_id}")
        except NoTranscriptFound:
            # Try to get auto-generated transcript with default language
            try:
                transcript = ytt_api.fetch(video_id)
            except Exception as e:
                raise ValueError(f"No transcript available for video: {video_id}. Error: {e}")
        except VideoUnavailable:
            raise ValueError(f"Video unavailable: {video_id}")
        except Exception as e:
            raise ValueError(f"Failed to get transcript: {e}")

        # Convert transcript to list of segments
        transcript_list = list(transcript)
        
        # Combine all transcript segments
        full_text = " ".join(entry.text for entry in transcript_list)
        
        # Calculate duration from last segment
        if transcript_list:
            last_segment = transcript_list[-1]
            duration_minutes = (last_segment.start + getattr(last_segment, 'duration', 0)) / 60
        else:
            duration_minutes = 0

        logger.info(f"Retrieved transcript: {len(full_text)} chars, {duration_minutes:.1f} minutes")
        return full_text, duration_minutes

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

Provide a detailed summary with the main points, key insights, and important takeaways from this section. Be specific and reference actual content from the transcript."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000
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
        """Async wrapper to run chunk summarization in thread pool."""
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
        
        # Get transcript
        transcript, duration_minutes = self.get_transcript(video_id)
        
        # Chunk the transcript for long videos
        chunks = self._chunk_transcript(transcript)
        
        # Summarize all chunks IN PARALLEL for speed
        logger.info(f"Summarizing {len(chunks)} chunks in parallel...")
        
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
        
        logger.info(f"All {len(chunks)} chunks processed in parallel")
        
        # Generate final summary and top learnings
        logger.info("Generating final summary and learnings...")
        loop = asyncio.get_event_loop()
        final_summary, top_learnings = await loop.run_in_executor(
            _executor,
            self._generate_final_summary,
            chunk_summaries
        )
        
        # Try to get video title (we'll use a placeholder for now)
        video_title = f"Video {video_id}"
        
        return VideoSummary(
            video_id=video_id,
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            title=video_title,
            transcript_length=len(transcript),
            summary=final_summary,
            top_learnings=top_learnings,
            duration_minutes=duration_minutes
        )

