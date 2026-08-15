import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { formatCount } from "@/lib/utils"

interface RepeatsDueCardProps {
  repeatsDue: number
  onStartReview: () => void
}

export function RepeatsDueCard({ repeatsDue, onStartReview }: RepeatsDueCardProps) {
  const count = repeatsDue !== undefined && repeatsDue !== null ? repeatsDue : 2

  return (
    <Card className="rounded-[12px] border border-border bg-card">
      <CardContent className="p-3.5 flex items-center justify-between gap-3">
        <div className="space-y-0.5">
          <div className="text-xs text-muted-foreground font-medium select-none">
            Powtórki na dziś
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-mono font-bold text-foreground tabular-nums leading-none">
              {formatCount(count || 2)}
            </span>
            <span className="text-xs text-muted-foreground select-none">
              pytania do powtórki
            </span>
          </div>
        </div>

        <Button
          onClick={onStartReview}
          variant="outline"
          className="shrink-0 h-8 px-3 text-xs font-semibold rounded-[8px] border-border text-foreground hover:bg-secondary select-none font-sans"
        >
          Powtórz →
        </Button>
      </CardContent>
    </Card>
  )
}
