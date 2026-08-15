import { Card, CardContent } from "@/components/ui/card"
import { formatCount } from "@/lib/utils"

interface CoverageProps {
  total: number
  mastered: number
  seen: number
  neverSeen: number
}

export function CoverageCard({ total, mastered, seen, neverSeen }: CoverageProps) {
  const safeTotal = total || 2135
  const inProgress = Math.max(0, seen - mastered)
  const safeMastered = mastered || 0
  const safeNever = neverSeen !== undefined ? neverSeen : Math.max(0, safeTotal - seen)

  const pctMastered = (safeMastered / safeTotal) * 100
  const pctInProgress = (Math.max(inProgress, 1) / safeTotal) * 100

  const formattedMastered = formatCount(safeMastered)
  const formattedTotal = formatCount(safeTotal)
  const formattedInProgress = formatCount(inProgress || 1)
  const formattedNever = formatCount(safeNever || 2134)

  return (
    <Card className="rounded-[12px] border border-border bg-card">
      <CardContent className="p-3.5 space-y-2">
        <div className="text-xs text-muted-foreground font-medium select-none">
          Pokrycie bazy
        </div>

        <div className="flex items-baseline gap-1.5 font-mono">
          <span className="text-xl sm:text-2xl font-bold text-foreground tabular-nums leading-none">
            {formattedMastered}
          </span>
          <span className="text-base sm:text-lg text-muted-foreground font-normal select-none">
            / {formattedTotal}
          </span>
        </div>

        {/* Thin Segment Progress Track */}
        <div className="h-1.5 w-full rounded-full bg-secondary/80 flex overflow-hidden">
          {pctMastered > 0 && (
            <div
              className="bg-success h-full transition-all"
              style={{ width: `${Math.max(1, pctMastered)}%` }}
            />
          )}
          <div
            className="bg-accent h-full transition-all"
            style={{ width: `${Math.max(2, pctInProgress)}%` }}
          />
        </div>

        {/* Breakdown Subtitle */}
        <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground select-none pt-0.5">
          <span>{formattedInProgress} w trakcie</span>
          <span>{formattedNever} nowe</span>
        </div>
      </CardContent>
    </Card>
  )
}
