import { Card, CardContent } from "@/components/ui/card"
import { History, Check, X } from "lucide-react"

interface ActivityItem {
  id: number
  question_id: number
  q_pl: string
  chosen: string
  is_correct: number
  time_ms: number
  created_at: string
}

interface RecentActivityFeedProps {
  activity: ActivityItem[]
}

export function RecentActivityFeed({ activity }: RecentActivityFeedProps) {
  return (
    <Card className="rounded-[12px] border border-border bg-card">
      <CardContent className="p-5 space-y-3.5">
        <div className="flex items-center justify-between select-none">
          <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
            <History className="w-3.5 h-3.5 text-accent" />
            <span>Ostatnie odpowiedzi</span>
          </div>
          <span className="text-[10px] font-mono text-muted-foreground">
            {activity.length} zdarzeń
          </span>
        </div>

        <div className="divide-y divide-border/60">
          {activity.length === 0 ? (
            <p className="text-xs font-mono text-muted-foreground py-3 select-none">Brak zarejestrowanych odpowiedzi.</p>
          ) : (
            activity.map((item) => {
              const isCorrect = Boolean(item.is_correct)
              const timeSec = (item.time_ms / 1000).toFixed(1)

              return (
                <div
                  key={item.id}
                  className="py-2 first:pt-1 last:pb-0 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 ${
                        isCorrect
                          ? "bg-success/15 text-success border border-success/40"
                          : "bg-destructive/15 text-destructive border border-destructive/40"
                      }`}
                    >
                      {isCorrect ? <Check className="w-2.5 h-2.5" /> : <X className="w-2.5 h-2.5" />}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 font-mono text-xs select-none">
                        <span className="font-bold text-foreground">
                          #{item.question_id}
                        </span>
                        <span className="text-muted-foreground">Odp:</span>
                        <strong className="text-foreground">{item.chosen}</strong>
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate max-w-[260px]">
                        {item.q_pl}
                      </p>
                    </div>
                  </div>

                  <div className="text-right shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums select-none">
                    <span>{timeSec}s</span>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </CardContent>
    </Card>
  )
}
