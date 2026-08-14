import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Flame } from "lucide-react"

interface HardestItem {
  id: number
  q_pl: string
  scope: string
  attempts: number
  wrong: number
  error_pct: number
  b_q: number
}

interface HardestQuestionsTableProps {
  questions: HardestItem[]
}

export function HardestQuestionsTable({ questions }: HardestQuestionsTableProps) {
  return (
    <Card className="rounded-[12px] border border-border bg-card">
      <CardContent className="p-5 space-y-3.5">
        <div className="flex items-center justify-between select-none">
          <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
            <Flame className="w-3.5 h-3.5 text-destructive" />
            <span>Najtrudniejsze pytania</span>
          </div>
          <span className="text-[10px] font-mono text-muted-foreground">
            Wskazania błędów
          </span>
        </div>

        <div className="divide-y divide-border/60">
          {questions.length === 0 ? (
            <p className="text-xs font-mono text-muted-foreground py-3 select-none">Brak zarejestrowanych trudnych pytań.</p>
          ) : (
            questions.map((q) => (
              <div key={q.id} className="py-2.5 first:pt-1 last:pb-0 space-y-1 group">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 font-mono text-xs select-none">
                    <span className="font-bold text-foreground">
                      #{q.id}
                    </span>
                    <Badge variant="outline" className="text-[10px] text-muted-foreground py-0 rounded-[4px]">
                      {q.scope}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1.5 font-mono text-xs select-none">
                    <span className="text-destructive font-semibold tabular-nums">
                      {q.error_pct}% błędów
                    </span>
                    <span className="text-[10px] text-muted-foreground tabular-nums">
                      ({q.attempts} prób)
                    </span>
                  </div>
                </div>
                <p className="text-xs text-foreground/80 line-clamp-1 leading-normal group-hover:text-foreground transition-colors">
                  {q.q_pl}
                </p>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
