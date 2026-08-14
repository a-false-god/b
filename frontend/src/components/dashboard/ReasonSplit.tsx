import { Card, CardContent } from "@/components/ui/card"

interface ReasonSplitProps {
  slips: number
  mistakes: number
  uncertainty: number
}

export function ReasonSplit({ slips, mistakes, uncertainty }: ReasonSplitProps) {
  const safeSlips = slips !== undefined ? slips : 0
  const safeMistakes = mistakes !== undefined ? mistakes : 2
  const safeUncertainty = uncertainty !== undefined ? uncertainty : 0

  return (
    <Card className="rounded-[12px] border border-border bg-card">
      <CardContent className="p-3.5 space-y-2">
        <div className="text-xs text-muted-foreground font-medium select-none">
          Typologia pomyłek
        </div>

        <div className="space-y-1.5 pt-0.5 select-none font-mono text-xs">
          {/* Pośpiech */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
              <span className="text-foreground font-sans font-normal text-xs">Pośpiech</span>
            </div>
            <span className="font-mono font-bold text-foreground tabular-nums">{safeSlips}</span>
          </div>

          {/* Trudne */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-destructive shrink-0" />
              <span className="text-foreground font-sans font-normal text-xs">Trudne</span>
            </div>
            <span className="font-mono font-bold text-foreground tabular-nums">{safeMistakes}</span>
          </div>

          {/* Wahania */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
              <span className="text-foreground font-sans font-normal text-xs">Wahania</span>
            </div>
            <span className="font-mono font-bold text-foreground tabular-nums">{safeUncertainty}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
