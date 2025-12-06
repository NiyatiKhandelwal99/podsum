"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Stepper, type StepperStep } from "@/components/ui/stepper"
import { ExternalLink, CheckCircle2, Play, Music, Sparkles, FileText, AlertCircle, X, Search } from "lucide-react"
import { summarizeYouTubeVideo, searchPodcast, ApiError } from "@/lib/api"
import { isYouTubeUrl } from "@/lib/utils"
import type { YouTubeSummarizeResponse } from "@/lib/types"
import { ProgressStep } from "@/lib/types"

/**
 * Format duration in minutes to a human-readable string (e.g., "1h 23m")
 */
function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const mins = Math.floor(minutes % 60)
  
  if (hours > 0 && mins > 0) {
    return `${hours}h ${mins}m`
  } else if (hours > 0) {
    return `${hours}h`
  } else {
    return `${mins}m`
  }
}

export default function Home() {
  const [input, setInput] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [summary, setSummary] = useState<YouTubeSummarizeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState<ProgressStep>(ProgressStep.IDLE)
  const [videoInfo, setVideoInfo] = useState<{ title?: string; url?: string; videoId?: string } | null>(null)
  const [isSearchQuery, setIsSearchQuery] = useState(false)

  // Define stepper steps based on whether it's a search query or direct URL
  const getStepperSteps = (): StepperStep[] => {
    if (isSearchQuery) {
      return [
        { id: ProgressStep.FINDING_VIDEO, label: "Finding episode", icon: Search },
        { id: ProgressStep.VIDEO_FOUND, label: "Video identified", icon: CheckCircle2 },
        { id: ProgressStep.GENERATING_TRANSCRIPT, label: "Fetching transcript", icon: FileText },
        { id: ProgressStep.SUMMARIZING, label: "Generating summary", icon: Sparkles },
        { id: ProgressStep.COMPLETE, label: "Complete", icon: CheckCircle2 },
      ]
    } else {
      return [
        { id: ProgressStep.GENERATING_TRANSCRIPT, label: "Fetching transcript", icon: FileText },
        { id: ProgressStep.SUMMARIZING, label: "Generating summary", icon: Sparkles },
        { id: ProgressStep.COMPLETE, label: "Complete", icon: CheckCircle2 },
      ]
    }
  }

  const handleGenerate = async () => {
    if (!input.trim()) return
    
    setIsGenerating(true)
    setError(null)
    setSummary(null)
    setVideoInfo(null)
    const isUrl = isYouTubeUrl(input)
    setIsSearchQuery(!isUrl)

    try {
      // Start progress tracking
      if (isUrl) {
        // Direct URL - start with transcript generation
        setCurrentStep(ProgressStep.GENERATING_TRANSCRIPT)
        
        // Simulate progress transitions
        setTimeout(() => {
          setCurrentStep(ProgressStep.SUMMARIZING)
        }, 2000)
      } else {
        // Search query - start with finding video
        setCurrentStep(ProgressStep.FINDING_VIDEO)
        
        // Simulate finding video step
        setTimeout(() => {
          setCurrentStep(ProgressStep.VIDEO_FOUND)
        }, 1500)
        
        // Then move to transcript
        setTimeout(() => {
          setCurrentStep(ProgressStep.GENERATING_TRANSCRIPT)
        }, 3000)
        
        // Then summarizing
        setTimeout(() => {
          setCurrentStep(ProgressStep.SUMMARIZING)
        }, 5000)
      }

      let result: YouTubeSummarizeResponse

      if (isUrl) {
        // User provided a YouTube URL
        result = await summarizeYouTubeVideo(input.trim())
      } else {
        // User provided a search query
        result = await searchPodcast(input.trim())
        
        // Extract video info when we get the result
        if (result) {
          setVideoInfo({
            title: result.title,
            url: result.video_url,
            videoId: result.video_id,
          })
        }
      }

      setSummary(result)
      setCurrentStep(ProgressStep.COMPLETE)
    } catch (err) {
      setCurrentStep(ProgressStep.IDLE)
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError("An unexpected error occurred. Please try again.")
      }
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border py-6 px-6 md:px-8">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-foreground/10 flex items-center justify-center">
              <Music className="w-4 h-4 text-foreground" />
            </div>
            <span className="text-lg font-semibold tracking-tight">Podsum</span>
          </div>
          <span className="text-xs font-medium px-2 py-1 bg-foreground/5 text-foreground/70 rounded">Beta</span>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 py-12 md:py-20 px-6 md:px-8">
        <div className="max-w-2xl mx-auto">
          {/* Hero Section */}
          <div className="mb-12">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-balance">
              Turn long podcasts into usable content.
            </h1>
            <p className="text-lg text-foreground/70 mb-8 text-balance">
              Paste a YouTube link or describe the podcast. Podsum finds it, summarizes it, and prepares it for export.
            </p>

            {/* Input Section */}
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground/70 block mb-2">
                  YouTube URL or podcast description
                </label>
                <Input
                  placeholder="Paste a YouTube URL or type 'Joe Rogan podcast with Elon Musk'…"
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value)
                    setError(null) // Clear error when user types
                  }}
                  onKeyDown={(e) => e.key === "Enter" && !isGenerating && handleGenerate()}
                  className="text-base h-12 bg-card border-input"
                  disabled={isGenerating}
                />
              </div>
              
              {/* Error Display */}
              {error && (
                <div className="flex items-start gap-3 p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                  <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-destructive font-medium mb-1">Error</p>
                    <div className="text-sm text-destructive/80 whitespace-pre-line">{error}</div>
                  </div>
                  <button
                    onClick={() => setError(null)}
                    className="text-destructive/60 hover:text-destructive transition-colors"
                    aria-label="Dismiss error"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              <Button
                onClick={handleGenerate}
                disabled={isGenerating || !input.trim()}
                className="w-full md:w-auto"
                size="lg"
              >
                {isGenerating ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                    Generating...
                  </div>
                ) : (
                  "Generate summary"
                )}
              </Button>
              <p className="text-xs text-foreground/50">
                Podsum uses AI to fetch the transcript, summarize it, and prepare export-ready content.
              </p>
            </div>
          </div>

          {/* Animated Stepper */}
          <AnimatePresence>
            {(isGenerating || summary) && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="mb-12 py-8 border-y border-border"
              >
                <Stepper currentStep={currentStep} steps={getStepperSteps()} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Video Preview Card (for search queries) */}
          <AnimatePresence>
            {currentStep === ProgressStep.VIDEO_FOUND && videoInfo && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4 }}
                className="mb-8"
              >
                <Card className="overflow-hidden">
                  <div className="flex gap-4 p-4">
                    {videoInfo.videoId && (
                      <img
                        src={`https://img.youtube.com/vi/${videoInfo.videoId}/maxresdefault.jpg`}
                        alt={videoInfo.title || "Video thumbnail"}
                        className="w-32 h-20 rounded-lg object-cover flex-shrink-0"
                        onError={(e) => {
                          // Fallback to default thumbnail if maxresdefault fails
                          const target = e.target as HTMLImageElement
                          target.src = `https://img.youtube.com/vi/${videoInfo.videoId}/hqdefault.jpg`
                        }}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-base mb-1 line-clamp-2">{videoInfo.title}</h3>
                      {videoInfo.url && (
                        <a
                          href={videoInfo.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors mt-2"
                        >
                          Open on YouTube
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Summary Area */}
          {summary ? (
            <div className="space-y-6">
              <Card className="overflow-hidden">
                <div className="grid md:grid-cols-2 gap-6 p-6">
                  {/* Left Panel - Episode Meta */}
                  <div className="space-y-4">
                    <div className="aspect-video bg-foreground/5 rounded-lg flex items-center justify-center">
                      <Play className="w-12 h-12 text-foreground/20" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg mb-1">{summary.title}</h3>
                      <p className="text-sm text-foreground/60">{formatDuration(summary.duration_minutes)}</p>
                      <p className="text-xs text-foreground/50 mt-1">
                        {summary.transcript_length.toLocaleString()} characters
                      </p>
                    </div>
                    <a
                      href={summary.video_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-primary hover:text-primary/80 transition-colors"
                    >
                      Open on YouTube
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  {/* Right Panel - Summary */}
                  <div>
                    <h3 className="font-semibold text-lg mb-4">Summary</h3>
                    <p className="text-sm text-foreground/70 mb-6 leading-relaxed">
                      {summary.summary}
                    </p>

                    <div>
                      <h4 className="font-semibold text-sm mb-3">Key points</h4>
                      <ul className="space-y-2">
                        {summary.top_learnings.map((point, idx) => (
                          <li key={idx} className="flex gap-3 text-sm text-foreground/70">
                            <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {summary.saved_to_notion && summary.notion_page_url && (
                      <div className="mt-6 p-3 rounded-lg bg-primary/5 border border-primary/20">
                        <p className="text-xs text-foreground/60 mb-1">
                          Summary saved to Notion
                        </p>
                        <a
                          href={summary.notion_page_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-primary hover:text-primary/80 inline-flex items-center gap-1"
                        >
                          Open in Notion
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}

                    <p className="text-xs text-foreground/40 mt-6">Generated using AI (DigitalOcean Gradient)</p>
                  </div>
                </div>
              </Card>

              {/* Export Section */}
              {summary.saved_to_notion && summary.notion_page_url ? (
                <div className="space-y-4 pt-2">
                  <div>
                    <h3 className="font-semibold text-lg mb-4">Export this summary</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <Button variant="outline" className="h-11 bg-transparent" disabled>
                        Instagram
                      </Button>
                      <Button variant="outline" className="h-11 bg-transparent" disabled>
                        Canva
                      </Button>
                      <Button 
                        className="h-11"
                        onClick={() => window.open(summary.notion_page_url!, "_blank")}
                      >
                        Open in Notion
                      </Button>
                    </div>
                  </div>
                  <p className="text-xs text-foreground/50">
                    Summary has been saved to Notion. Instagram and Canva exports are coming soon.
                  </p>
                </div>
              ) : (
                <div className="space-y-4 pt-2">
                  <div>
                    <h3 className="font-semibold text-lg mb-4">Export this summary</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <Button variant="outline" className="h-11 bg-transparent" disabled>
                        Instagram
                      </Button>
                      <Button variant="outline" className="h-11 bg-transparent" disabled>
                        Canva
                      </Button>
                      <Button className="h-11" disabled>
                        Notion
                      </Button>
                    </div>
                  </div>
                  <p className="text-xs text-foreground/50">
                    Notion export is available today. Instagram and Canva exports are coming soon.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <Card className="p-12 text-center border-dashed">
              <div className="flex justify-center mb-4">
                <div className="w-12 h-12 rounded-lg bg-foreground/5 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-foreground/30" />
                </div>
              </div>
              <p className="text-foreground/50">Your summary will appear here after generation.</p>
            </Card>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-6 md:px-8 mt-12">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-sm text-foreground/60 mb-2">Podsum · Podcast → content summarization</p>
          <p className="text-xs text-foreground/40">Backend powered by DigitalOcean Gradient and Tadata</p>
        </div>
      </footer>
    </main>
  )
}
