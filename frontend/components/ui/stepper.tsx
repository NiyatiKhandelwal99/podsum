"use client"

import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2, Loader2, Search, Play, FileText, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ProgressStep } from "@/lib/types"

export interface StepperStep {
  id: ProgressStep
  label: string
  icon: React.ComponentType<{ className?: string }>
  showForSearch?: boolean
}

interface StepperProps {
  currentStep: ProgressStep
  steps: StepperStep[]
  className?: string
}

const stepVariants = {
  pending: {
    scale: 1,
    opacity: 0.4,
    backgroundColor: "var(--muted)",
    color: "var(--muted-foreground)",
  },
  active: {
    scale: 1.1,
    opacity: 1,
    backgroundColor: "var(--primary)",
    color: "var(--primary-foreground)",
  },
  complete: {
    scale: 1,
    opacity: 1,
    backgroundColor: "var(--primary)",
    color: "var(--primary-foreground)",
  },
}

const iconVariants = {
  pending: { scale: 1, rotate: 0 },
  active: { scale: 1, rotate: 360 },
  complete: { scale: [0, 1.2, 1], rotate: 0 },
}

export function Stepper({ currentStep, steps, className }: StepperProps) {
  const getStepState = (stepId: ProgressStep, current: ProgressStep): "pending" | "active" | "complete" => {
    const stepIndex = steps.findIndex((s) => s.id === stepId)
    const currentIndex = steps.findIndex((s) => s.id === current)

    if (stepIndex < currentIndex) return "complete"
    if (stepIndex === currentIndex) return "active"
    return "pending"
  }

  const getProgressPercent = (): number => {
    const currentIndex = steps.findIndex((s) => s.id === currentStep)
    if (currentIndex === -1) return 0
    return (currentIndex / (steps.length - 1)) * 100
  }

  return (
    <div className={cn("w-full", className)}>
      <div className="relative flex items-center">
        {steps.map((step, index) => {
          const state = getStepState(step.id, currentStep)
          const Icon = step.icon
          const isLast = index === steps.length - 1
          const prevState = index > 0 ? getStepState(steps[index - 1].id, currentStep) : "pending"

          return (
            <React.Fragment key={step.id}>
              {/* Step Indicator */}
              <motion.div
                className="relative z-10 flex flex-col items-center gap-2 flex-shrink-0"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.3 }}
              >
                <motion.div
                  className={cn(
                    "relative flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors",
                    state === "pending" && "border-muted bg-muted/50",
                    state === "active" && "border-primary bg-primary",
                    state === "complete" && "border-primary bg-primary"
                  )}
                  animate={stepVariants[state]}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  <AnimatePresence mode="wait">
                    {state === "active" ? (
                      <motion.div
                        key="loading"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      >
                        <Loader2 className="h-5 w-5" />
                      </motion.div>
                    ) : state === "complete" ? (
                      <motion.div
                        key="check"
                        initial={{ scale: 0 }}
                        animate={{ scale: [0, 1.2, 1] }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                      >
                        <CheckCircle2 className="h-5 w-5" />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="icon"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.2 }}
                      >
                        <Icon className="h-5 w-5" />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
                <motion.span
                  className={cn(
                    "text-xs font-medium text-center max-w-[80px]",
                    state === "pending" && "text-muted-foreground",
                    state === "active" && "text-primary font-semibold",
                    state === "complete" && "text-primary"
                  )}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.1 + 0.2 }}
                >
                  {step.label}
                </motion.span>
              </motion.div>

              {/* Connecting Line */}
              {!isLast && (
                <div className="relative flex-1 h-0.5 mx-2 bg-muted -z-0">
                  <motion.div
                    className="h-full bg-primary"
                    initial={{ width: 0 }}
                    animate={{ width: prevState === "complete" ? "100%" : state === "active" ? "50%" : "0%" }}
                    transition={{ duration: 0.5, ease: "easeInOut" }}
                  />
                </div>
              )}
            </React.Fragment>
          )
        })}
      </div>

      {/* Overall Progress Bar */}
      <motion.div
        className="mt-6 h-1 w-full rounded-full bg-muted overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <motion.div
          className="h-full bg-primary rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${getProgressPercent()}%` }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
        />
      </motion.div>
    </div>
  )
}

