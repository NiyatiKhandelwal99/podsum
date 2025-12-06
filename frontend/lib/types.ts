/** TypeScript types matching backend API models */

export interface YouTubeSummarizeRequest {
  url: string
}

export interface SearchRequest {
  query: string
}

export interface YouTubeSummarizeResponse {
  video_id: string
  video_url: string
  title: string
  transcript_length: number
  duration_minutes: number
  summary: string
  top_learnings: string[]
  notion_page_url: string | null
  saved_to_notion: boolean
}

export interface ApiError {
  detail: string
}

/** Progress step states for the video processing workflow */
export enum ProgressStep {
  IDLE = "idle",
  FINDING_VIDEO = "finding_video",
  VIDEO_FOUND = "video_found",
  GENERATING_TRANSCRIPT = "generating_transcript",
  SUMMARIZING = "summarizing",
  COMPLETE = "complete",
}

/** Progress state tracking */
export interface ProgressState {
  currentStep: ProgressStep
  videoInfo?: {
    title?: string
    url?: string
    videoId?: string
  } | null
}

