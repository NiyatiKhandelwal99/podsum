import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Check if a string is a YouTube URL
 */
export function isYouTubeUrl(input: string): boolean {
  if (!input || typeof input !== "string") {
    return false
  }

  const trimmed = input.trim().toLowerCase()
  
  // Common YouTube URL patterns
  const youtubePatterns = [
    /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/i,
    /^https?:\/\/youtu\.be\/[\w-]+/i,
    /^https?:\/\/(www\.)?youtube\.com\/embed\/[\w-]+/i,
    /^https?:\/\/(www\.)?youtube\.com\/v\/[\w-]+/i,
  ]

  return youtubePatterns.some((pattern) => pattern.test(trimmed))
}
