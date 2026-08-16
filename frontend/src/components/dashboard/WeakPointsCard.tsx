import { Card, CardContent } from "@/components/ui/card"

export interface WeakPointItem {
  axis_b: string
  label: string
  accuracy_pct: number
  error_count: number
  theta?: number
}

interface WeakPointsCardProps {
  weakPoints?: WeakPointItem[]
  onSelectDomain: (axisB: string) => void
}

const DEFAULT_WEAK_POINTS: WeakPointItem[] = [
  { axis_b: "znaki_i_sygnaly", label: "znaki i sygnały", accuracy_pct: 62, error_count: 3 },
  { axis_b: "administracja_i_kary", label: "przepisy ruchu", accuracy_pct: 48, error_count: 5 },
  { axis_b: "technika_pojazdu", label: "obsługa pojazdu", accuracy_pct: 71, error_count: 2 },
]

export function WeakPointsCard({
  weakPoints = DEFAULT_WEAK_POINTS,
  onSelectDomain,
}: WeakPointsCardProps) {
  const items = weakPoints && weakPoints.length > 0 ? weakPoints.slice(0, 4) : DEFAULT_WEAK_POINTS

  return (
    <Card className="rounded-[14px] border border-border bg-card shadow-none overflow-hidden">
      <CardContent className="p-4 sm:p-5 space-y-3">
        {/* Header Tag */}
        <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground select-none font-medium">
          SŁABE PUNKTY · TAP = SESJA Z FILTREM
        </div>

        {/* List of Weak Domain Rows */}
        <div className="space-y-1 pt-1">
          {items.map((item) => {
            const pct = Math.min(100, Math.max(0, item.accuracy_pct))

            return (
              <div
                key={item.axis_b}
                onClick={() => onSelectDomain(item.axis_b)}
                className="group flex items-center justify-between gap-3 py-1.5 px-2 -mx-2 rounded-[8px] hover:bg-secondary/50 active:bg-secondary/70 cursor-pointer transition-colors select-none"
                title={`Rozpocznij sesję z działu: ${item.label}`}
              >
                {/* Domain Title */}
                <span className="text-xs sm:text-sm font-medium text-foreground truncate min-w-[100px] sm:min-w-[120px] group-hover:text-accent transition-colors">
                  {item.label}
                </span>

                {/* Progress Track */}
                <div className="flex-1 max-w-[130px] sm:max-w-[160px] h-1.5 rounded-full bg-secondary/80 overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500 ease-out group-hover:brightness-110"
                    style={{ width: `${pct}%` }}
                  />
                </div>

                {/* Accuracy Percentage */}
                <span className="font-mono text-xs text-muted-foreground tabular-nums w-8 text-right group-hover:text-foreground">
                  {item.accuracy_pct === 0 && item.error_count === 0 ? "0%" : `${Math.round(pct)}%`}
                </span>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
