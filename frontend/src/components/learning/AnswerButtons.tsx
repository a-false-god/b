import { useState, useEffect } from "react"
import { Check, X } from "lucide-react"

interface AnswerButtonsProps {
  type: "TN" | "ABC"
  aPl?: string | null
  bPl?: string | null
  cPl?: string | null
  answered: boolean
  chosenOption: string | null
  correctOption: string | null
  isCorrect: boolean | null
  onSelect: (option: string) => void
  disabled?: boolean
}

export function AnswerButtons({
  type,
  aPl,
  bPl,
  cPl,
  answered,
  chosenOption,
  correctOption,
  onSelect,
  disabled = false,
}: AnswerButtonsProps) {
  const [stagedOption, setStagedOption] = useState<string | null>(null)
  const [isCoarsePointer, setIsCoarsePointer] = useState(false)

  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia) {
      const mql = window.matchMedia("(pointer: coarse)")
      setIsCoarsePointer(mql.matches)
      const handler = (e: MediaQueryListEvent) => setIsCoarsePointer(e.matches)
      mql.addEventListener("change", handler)
      return () => mql.removeEventListener("change", handler)
    }
  }, [])

  // Clear staged option when answered or when options reset
  useEffect(() => {
    if (answered || chosenOption) {
      setStagedOption(null)
    }
  }, [answered, chosenOption])

  const options =
    type === "TN"
      ? [
          { key: "T", label: "TAK" },
          { key: "N", label: "NIE" },
        ]
      : [
          { key: "A", label: aPl || "" },
          { key: "B", label: bPl || "" },
          { key: "C", label: cPl || "" },
        ]

  const handleOptionClick = (key: string) => {
    if (disabled || answered) return

    if (isCoarsePointer) {
      // D6 Touch commit: first tap selects, second commits
      if (stagedOption === key) {
        onSelect(key)
        setStagedOption(null)
      } else {
        setStagedOption(key)
      }
    } else {
      // Mouse click commits immediately
      onSelect(key)
    }
  }

  const handleConfirmStaged = () => {
    if (stagedOption && !answered && !disabled) {
      onSelect(stagedOption)
      setStagedOption(null)
    }
  }

  return (
    <div className="grid gap-2 w-full">
      {options.map((opt) => {
        const isThisChosen = chosenOption === opt.key
        const isThisCorrect = correctOption === opt.key
        const isStaged = stagedOption === opt.key

        let containerClasses =
          "border border-border bg-card text-foreground hover:border-accent"
        let badgeClasses =
          "border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent"
        let rightIcon = null

        if (!answered && isStaged) {
          containerClasses = "border border-accent bg-accent-soft text-foreground ring-1 ring-accent"
          badgeClasses = "border border-accent bg-accent text-accent-foreground font-bold"
        }

        if (answered) {
          if (isThisCorrect) {
            containerClasses = "border border-success bg-success-soft text-foreground"
            badgeClasses = "border border-success/40 bg-success/20 text-foreground font-bold"
            rightIcon = <Check className="w-4 h-4 text-success shrink-0 ml-auto" strokeWidth={2.5} />
          } else if (isThisChosen && !isThisCorrect) {
            containerClasses = "border border-destructive bg-destructive-soft text-foreground"
            badgeClasses = "border border-destructive/40 bg-destructive/20 text-foreground font-bold"
            rightIcon = <X className="w-4 h-4 text-destructive shrink-0 ml-auto" strokeWidth={2.5} />
          } else {
            // Unselected options restore full neutral styling (calm, full contrast, no /80 dimming)
            containerClasses = "border border-border bg-card text-foreground"
            badgeClasses = "border border-border bg-secondary text-muted-foreground"
          }
        }

        return (
          <button
            key={opt.key}
            type="button"
            disabled={disabled || answered}
            onClick={() => handleOptionClick(opt.key)}
            className={`group relative flex items-center justify-between text-left min-h-[64px] py-3.5 px-4 rounded-[12px] transition-colors duration-fast active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed select-none ${containerClasses}`}
          >
            <div className="flex items-center gap-3.5 flex-1 pr-2">
              {/* Kbd badge: 30x30 left, hidden on (pointer:coarse) */}
              <span
                className={`hidden [@media(pointer:fine)]:inline-flex items-center justify-center w-[30px] h-[30px] rounded-[8px] text-xs font-mono font-bold shrink-0 transition-colors select-none tabular-nums ${badgeClasses}`}
              >
                {opt.key}
              </span>
              <span className="text-type-body font-normal leading-snug text-foreground flex-1">
                {opt.label}
              </span>
            </div>
            {rightIcon}
          </button>
        )
      })}

      {/* D6 Touch commit confirmation button (revealed when an option is staged on pointer:coarse) */}
      {isCoarsePointer && stagedOption && !answered && (
        <button
          type="button"
          onClick={handleConfirmStaged}
          className="w-full h-11 mt-1 rounded-[10px] bg-accent text-accent-foreground font-mono font-semibold text-xs tracking-wider uppercase transition-opacity hover:opacity-90 active:scale-[0.99] animate-fade-in-up"
        >
          Sprawdź odpowiedź ({stagedOption})
        </button>
      )}
    </div>
  )
}
