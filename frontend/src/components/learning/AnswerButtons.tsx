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

  return (
    <div className="grid gap-3 w-full mt-4">
      {options.map((opt) => {
        const isThisChosen = chosenOption === opt.key
        const isThisCorrect = correctOption === opt.key

        let containerClasses =
          "border-[1.5px] border-border bg-card text-card-foreground hover:border-accent"
        let badgeClasses =
          "border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent"
        let statusIcon = null

        if (answered) {
          if (isThisCorrect) {
            containerClasses = "border-[1.5px] border-success bg-success/15 text-foreground"
            badgeClasses = "border border-success/40 bg-success/25 text-foreground font-bold"
            statusIcon = (
              <div className="w-6 h-6 rounded-full bg-success/20 flex items-center justify-center ml-auto shrink-0 animate-confirm-pop">
                <Check className="w-4 h-4 text-success" strokeWidth={2.5} />
              </div>
            )
          } else if (isThisChosen && !isThisCorrect) {
            containerClasses = "border-[1.5px] border-destructive bg-destructive/15 text-foreground"
            badgeClasses = "border border-destructive/40 bg-destructive/25 text-foreground font-bold"
            statusIcon = (
              <div className="w-6 h-6 rounded-full bg-destructive/20 flex items-center justify-center ml-auto shrink-0 animate-confirm-pop">
                <X className="w-4 h-4 text-destructive" strokeWidth={2.5} />
              </div>
            )
          } else {
            containerClasses = "border-[1.5px] border-border/60 bg-card/60 opacity-60 text-muted-foreground"
            badgeClasses = "border border-border/60 bg-secondary/50 text-muted-foreground"
          }
        }

        return (
          <button
            key={opt.key}
            type="button"
            disabled={disabled || answered}
            onClick={() => onSelect(opt.key)}
            className={`group relative flex items-center justify-between text-left min-h-[64px] py-3.5 px-4 rounded-[12px] transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed select-none ${containerClasses} ${
              answered && (isThisCorrect || isThisChosen) ? "animate-confirm-pop" : ""
            }`}
          >
            <div className="flex items-center gap-3.5 w-full pr-2">
              <span
                className={`inline-flex items-center justify-center w-[30px] h-[30px] rounded-[8px] text-xs font-mono font-bold shrink-0 transition-colors select-none tabular-nums ${badgeClasses}`}
              >
                {opt.key}
              </span>
              <span className="text-sm sm:text-base font-normal leading-snug text-foreground/95 flex-1">
                {opt.label}
              </span>
            </div>
            {statusIcon}
          </button>
        )
      })}
    </div>
  )
}
