import { useEffect, useRef } from "react"

interface SwipeHandlers {
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  disabled?: boolean
}

export function useTouchSwipe({
  onSwipeLeft,
  onSwipeRight,
  disabled = false,
}: SwipeHandlers) {
  const startXRef = useRef<number>(0)
  const startYRef = useRef<number>(0)

  useEffect(() => {
    if (disabled) return

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        startXRef.current = e.touches[0].screenX
        startYRef.current = e.touches[0].screenY
      }
    }

    const handleTouchEnd = (e: TouchEvent) => {
      if (e.changedTouches.length > 0) {
        const endX = e.changedTouches[0].screenX
        const endY = e.changedTouches[0].screenY
        const diffX = endX - startXRef.current
        const diffY = endY - startYRef.current

        // Horizontal swipe threshold: > 60px horizontal, < 40px vertical
        if (Math.abs(diffX) > 60 && Math.abs(diffY) < 40) {
          if (diffX < 0 && onSwipeLeft) {
            onSwipeLeft() // Swiped left -> next question
          } else if (diffX > 0 && onSwipeRight) {
            onSwipeRight() // Swiped right -> previous question
          }
        }
      }
    }

    window.addEventListener("touchstart", handleTouchStart, { passive: true })
    window.addEventListener("touchend", handleTouchEnd, { passive: true })

    return () => {
      window.removeEventListener("touchstart", handleTouchStart)
      window.removeEventListener("touchend", handleTouchEnd)
    }
  }, [onSwipeLeft, onSwipeRight, disabled])
}
