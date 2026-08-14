import { useEffect } from "react"

interface HotkeyHandlers {
  onPrev?: () => void
  onNext?: () => void
  onAnswer?: (choice: string) => void
  onToggleExplanation?: () => void
  onReviewAction?: (actionNumber: number) => void
  disabled?: boolean
}

export function useHotkeys({
  onPrev,
  onNext,
  onAnswer,
  onToggleExplanation,
  onReviewAction,
  disabled = false,
}: HotkeyHandlers) {
  useEffect(() => {
    if (disabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // Guard: Ignore keystrokes when focus is in an input, textarea, select, or editable element
      const target = e.target as HTMLElement | null
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable ||
          target.closest('[role="dialog"] input'))
      ) {
        return
      }

      const key = e.key.toUpperCase()

      // Navigation
      if (e.key === "ArrowLeft") {
        if (onPrev) {
          e.preventDefault()
          onPrev()
        }
      } else if (e.key === "ArrowRight") {
        if (onNext) {
          e.preventDefault()
          onNext()
        }
      }

      // Answers
      if (["T", "N", "A", "B", "C"].includes(key)) {
        if (onAnswer) {
          e.preventDefault()
          onAnswer(key)
        }
      }

      // Explanation toggle
      if (key === "E") {
        if (onToggleExplanation) {
          e.preventDefault()
          onToggleExplanation()
        }
      }

      // Review Queue actions 1-4
      if (["1", "2", "3", "4"].includes(e.key)) {
        if (onReviewAction) {
          e.preventDefault()
          onReviewAction(parseInt(e.key, 10))
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onPrev, onNext, onAnswer, onToggleExplanation, onReviewAction, disabled])
}
