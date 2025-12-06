/** API client for backend endpoints */

import type { YouTubeSummarizeResponse, ApiError as ApiErrorResponse } from "./types"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const REQUEST_TIMEOUT = 5 * 60 * 1000 // 5 minutes for long videos

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public detail?: string
  ) {
    super(message)
    this.name = "ApiError"
  }
}

/**
 * Summarize a YouTube video by URL
 */
export async function summarizeYouTubeVideo(
  url: string
): Promise<YouTubeSummarizeResponse> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

  try {
    const response = await fetch(`${API_BASE_URL}/api/youtube/summarize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      let errorDetail = "An error occurred while processing your request."
      try {
        const errorData: ApiErrorResponse = await response.json()
        errorDetail = errorData.detail || errorDetail
      } catch {
        // If response is not JSON, use default message
      }

      throw new ApiError(
        getErrorMessage(response.status, errorDetail),
        response.status,
        errorDetail
      )
    }

    return await response.json()
  } catch (error) {
    clearTimeout(timeoutId)

    if (error instanceof ApiError) {
      throw error
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError(
        "Request is taking longer than expected. This may take a few minutes for long videos.",
        408
      )
    }

    // Network errors
    throw new ApiError(
      "Unable to connect to server. Please check if the backend is running.",
      0
    )
  }
}

/**
 * Search for a podcast and generate summary
 */
export async function searchPodcast(
  query: string
): Promise<YouTubeSummarizeResponse> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

  try {
    const response = await fetch(`${API_BASE_URL}/api/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      let errorDetail = "An error occurred while processing your request."
      try {
        const errorData: ApiErrorResponse = await response.json()
        errorDetail = errorData.detail || errorDetail
      } catch {
        // If response is not JSON, use default message
      }

      throw new ApiError(
        getErrorMessage(response.status, errorDetail),
        response.status,
        errorDetail
      )
    }

    return await response.json()
  } catch (error) {
    clearTimeout(timeoutId)

    if (error instanceof ApiError) {
      throw error
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError(
        "Request is taking longer than expected. This may take a few minutes for long videos.",
        408
      )
    }

    // Network errors
    throw new ApiError(
      "Unable to connect to server. Please check if the backend is running.",
      0
    )
  }
}

/**
 * Get user-friendly error message based on status code
 */
function getErrorMessage(statusCode: number, detail: string): string {
  // Always return the detail message if available, as it may contain helpful instructions
  if (detail) {
    return detail
  }
  
  switch (statusCode) {
    case 400:
      return "Invalid request. Please check your input."
    case 404:
      return "Could not find the requested resource."
    case 500:
      return "An error occurred while processing your request. Please try again."
    default:
      return "An unexpected error occurred."
  }
}

