import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface ExamReadinessCardProps {
  score: number
  maxScore?: number
  passThreshold?: number
  scoreDelta?: number
  pointsNeeded?: number
  examsThisWeek?: number
  onOpenExam: () => void
}

export function ExamReadinessCard({
  score = 61,
  maxScore = 74,
  passThreshold = 68,
  scoreDelta = 6,
  pointsNeeded = 7,
  examsThisWeek = 3,
  onOpenExam,
}: ExamReadinessCardProps) {
  const currentScore = score || 61
  const passScore = passThreshold || 68
  const max = maxScore || 74
  const fillPct = Math.min(100, Math.max(0, (currentScore / max) * 100))
  const thresholdPct = Math.min(100, Math.max(0, (passScore / max) * 100))

  return (
    <Card className="rounded-[14px] border border-border bg-card shadow-none overflow-hidden">
      <CardContent className="p-4 sm:p-5 space-y-3.5">
        {/* Header Tag */}
        <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground select-none font-medium">
          GOTOWOŚĆ DO EGZAMINU
        </div>

        {/* Hero Score & Threshold Gauge Row */}
        <div className="flex items-center justify-between gap-3">
          {/* Left: 61/74 pkt */}
          <div className="flex items-baseline">
            <span className="text-[30px] sm:text-[34px] font-mono font-bold tracking-tight text-foreground tabular-nums leading-none">
              {currentScore}
            </span>
            <span className="text-sm font-mono text-muted-foreground font-normal ml-1 select-none">
              /{max} pkt
            </span>
          </div>

          {/* Right: Threshold Indicator */}
          <div className="flex flex-col items-end gap-1.5 min-w-[110px]">
            <div className="px-2 py-0.5 rounded-[4px] border border-border bg-secondary/40 text-muted-foreground font-mono text-[10px] select-none">
              próg: {passScore}
            </div>

            {/* Horizontal Mini Gauge with Threshold Pip */}
            <div className="relative w-full h-1.5 bg-secondary/80 rounded-full overflow-visible">
              {/* Score Fill */}
              <div
                className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
                style={{ width: `${fillPct}%` }}
              />
              {/* Orange/Amber Passing Threshold Marker */}
              <div
                className="absolute -top-[3px] w-[2px] h-3 bg-[#DE9255] rounded-full shadow-sm"
                style={{ left: `${thresholdPct}%` }}
                title={`Próg zdawalności: ${passScore} pkt`}
              />
            </div>
          </div>
        </div>

        {/* Subtitle */}
        <div className="text-xs text-muted-foreground select-none flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
          {examsThisWeek > 0 ? (
            <>
              <span className="text-emerald-500 dark:text-emerald-400 font-semibold tabular-nums">
                {scoreDelta >= 0 ? `+${scoreDelta}` : scoreDelta} od poprzedniego
              </span>
              <span>·</span>
              <span>
                {currentScore >= passScore
                  ? "zdany próg"
                  : `brakuje ${pointsNeeded > 0 ? pointsNeeded : Math.max(0, passScore - currentScore)} pkt`}
              </span>
              <span>·</span>
              <span>
                <strong className="text-foreground font-semibold tabular-nums">
                  {examsThisWeek}
                </strong>{" "}
                {examsThisWeek === 1 ? "sprawdzian" : examsThisWeek < 5 ? "sprawdziany" : "sprawdzianów"} w tyg.
              </span>
            </>
          ) : (
            <>
              <span>Próg zdawalności: <strong className="text-foreground font-semibold tabular-nums">{passScore} pkt</strong></span>
              <span>·</span>
              <span>Wykonaj pierwszy sprawdzian</span>
            </>
          )}
        </div>

        {/* Action Button */}
        <Button
          onClick={onOpenExam}
          variant="outline"
          className="w-full h-11 mt-1 rounded-[10px] border border-border/90 bg-card hover:bg-secondary/50 text-foreground font-semibold text-sm transition-all flex items-center justify-center select-none shadow-none font-sans"
        >
          Sprawdzian · 25 min
        </Button>
      </CardContent>
    </Card>
  )
}
