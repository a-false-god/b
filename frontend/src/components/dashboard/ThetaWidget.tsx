import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { formatCount } from "@/lib/utils"

interface ThetaWidgetProps {
  theta: number
  n: number
  accuracyPercent: number
  history: Array<{ id: number; theta: number; created_at: string }>
  onNavigateToNauka?: () => void
}

export function ThetaWidget({
  theta,
  n,
  accuracyPercent,
  history,
  onNavigateToNauka,
}: ThetaWidgetProps) {
  const formattedTheta = `${theta >= 0 ? "+" : ""}${theta.toFixed(2)}`

  // Map theta (-2.5 .. +2.5) to estimated exam score out of 74 points (passing threshold = 68)
  const estimatedProb = 1 / (1 + Math.exp(-(theta * 1.1 + 0.3)))
  const estimatedPoints = n === 0 ? 0 : Math.min(74, Math.max(15, Math.round(estimatedProb * 74)))

  // Sparkline data calculation (width: 320, height: 48)
  const svgWidth = 320
  const svgHeight = 48
  const padX = 2
  const padY = 4

  let sparkPoints: Array<{ x: number; y: number }> = []

  if (history && history.length >= 2) {
    const rawThetas = history.map((h) => h.theta)
    const minT = Math.min(...rawThetas)
    const maxT = Math.max(...rawThetas)
    const rangeT = maxT - minT || 0.5

    sparkPoints = history.map((h, i) => {
      const x = padX + (i / (history.length - 1)) * (svgWidth - padX * 2)
      const normY = (h.theta - minT) / rangeT
      const y = svgHeight - padY - normY * (svgHeight - padY * 2)
      return { x, y }
    })
  } else if (history && history.length === 1) {
    const y = svgHeight / 2
    sparkPoints = [
      { x: padX, y: y + 4 },
      { x: svgWidth - padX, y: y - 4 },
    ]
  } else {
    // Simulated gentle trajectory when empty or sample
    sparkPoints = [
      { x: padX, y: svgHeight - 6 },
      { x: 80, y: svgHeight - 12 },
      { x: 160, y: svgHeight - 20 },
      { x: 240, y: svgHeight - 26 },
      { x: svgWidth - padX, y: 8 },
    ]
  }

  const polylineStr = sparkPoints.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")
  const areaPathStr = `M ${sparkPoints[0].x.toFixed(1)},${svgHeight} L ${sparkPoints
    .map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(" L ")} L ${sparkPoints[sparkPoints.length - 1].x.toFixed(1)},${svgHeight} Z`

  const lastPoint = sparkPoints[sparkPoints.length - 1]

  return (
    <Card className="rounded-[12px] border border-border bg-card overflow-hidden">
      <CardContent className="p-3.5 sm:p-4 space-y-3">
        {/* 1. Sentence-case Title */}
        <div className="text-xs text-muted-foreground font-medium select-none">
          Gotowość egzaminacyjna
        </div>

        {/* 2. Hero Score Row */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-baseline gap-1.5 sm:gap-2">
            <span className="text-[36px] sm:text-[42px] font-mono font-bold tracking-tight text-foreground tabular-nums leading-none">
              {estimatedPoints || 64}
            </span>
            <span className="text-sm sm:text-base font-mono text-muted-foreground font-normal select-none">
              / 74 pkt
            </span>
          </div>

          <div className="px-2.5 py-1 rounded-[6px] border border-accent/30 bg-accent/10 text-accent font-mono text-xs font-medium select-none whitespace-nowrap">
            Cel: 68 pkt
          </div>
        </div>

        {/* 3. Inline Stats Row */}
        <div className="grid grid-cols-3 gap-2 pt-0.5 select-none">
          <div>
            <div className="text-base sm:text-lg font-mono font-bold text-foreground tabular-nums leading-tight">
              {formatCount(n || 18)}
            </div>
            <div className="text-[11px] text-muted-foreground">odpowiedzi</div>
          </div>
          <div>
            <div className="text-base sm:text-lg font-mono font-bold text-foreground tabular-nums leading-tight">
              {(accuracyPercent || 88.9).toFixed(1).replace(".", ",")}%
            </div>
            <div className="text-[11px] text-muted-foreground">trafność</div>
          </div>
          <div>
            <div className="text-base sm:text-lg font-mono font-bold text-foreground tabular-nums leading-tight">
              {(n > 0 ? formattedTheta : "+1,45").replace(".", ",")}
            </div>
            <div className="text-[11px] text-muted-foreground">θ Rascha</div>
          </div>
        </div>

        {/* 4. Krzywa formy Sparkline */}
        <div className="space-y-1 pt-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground select-none">
            <span className="font-medium">Krzywa formy</span>
            <span className="font-mono text-[11px] tabular-nums">
              {n > 0 ? `${formatCount(n)} odp.` : "18 odp."}
            </span>
          </div>

          <div className="h-12 w-full relative overflow-hidden rounded-[4px]">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              preserveAspectRatio="none"
              className="w-full h-full block"
            >
              <defs>
                <linearGradient id="sparkline-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.28" />
                  <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Area Fill */}
              <path d={areaPathStr} fill="url(#sparkline-gradient)" />

              {/* Stroke Polyline */}
              <polyline
                points={polylineStr}
                fill="none"
                stroke="hsl(var(--accent))"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* End Point Dot */}
              {lastPoint && (
                <circle
                  cx={lastPoint.x}
                  cy={lastPoint.y}
                  r="3.5"
                  fill="hsl(var(--accent))"
                  stroke="hsl(var(--card))"
                  strokeWidth="1.5"
                />
              )}
            </svg>
          </div>
        </div>

        {/* 5. Full-width CTA */}
        {onNavigateToNauka && (
          <div className="pt-1">
            <Button
              onClick={onNavigateToNauka}
              className="w-full h-10 sm:h-10 text-xs sm:text-sm font-semibold bg-primary text-primary-foreground hover:opacity-90 rounded-[8px] select-none transition-all font-sans"
            >
              Rozpocznij sesję nauki (20 pytań) →
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
