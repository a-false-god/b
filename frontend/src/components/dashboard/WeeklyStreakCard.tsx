import { Card, CardContent } from "@/components/ui/card"
import { Check } from "lucide-react"

interface DayItem {
  day_short: string
  date: string
  completed: boolean
  is_today: boolean
  is_future?: boolean
  answers_count?: number
}

interface WeeklyStreakCardProps {
  currentStreak?: number
  maxStreak?: number
  avgDailyQuestions?: number
  weekDays?: DayItem[]
}

const DEFAULT_WEEK_DAYS: DayItem[] = [
  { day_short: "pn", date: "2026-08-10", completed: true, is_today: false },
  { day_short: "wt", date: "2026-08-11", completed: true, is_today: false },
  { day_short: "śr", date: "2026-08-12", completed: true, is_today: false },
  { day_short: "cz", date: "2026-08-13", completed: true, is_today: false },
  { day_short: "pt", date: "2026-08-14", completed: false, is_today: false },
  { day_short: "so", date: "2026-08-15", completed: false, is_today: false },
  { day_short: "nd", date: "2026-08-16", completed: false, is_today: true },
]

export function WeeklyStreakCard({
  currentStreak = 4,
  maxStreak = 6,
  avgDailyQuestions = 22,
  weekDays = DEFAULT_WEEK_DAYS,
}: WeeklyStreakCardProps) {
  const days = weekDays && weekDays.length === 7 ? weekDays : DEFAULT_WEEK_DAYS

  return (
    <Card className="rounded-[14px] border border-border bg-card shadow-none overflow-hidden">
      <CardContent className="p-4 sm:p-5 space-y-4">
        {/* Header Tag */}
        <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground select-none font-medium">
          TEN TYDZIEŃ
        </div>

        {/* 7 Days Circle Row */}
        <div className="flex items-center justify-between px-1">
          {days.map((d, i) => {
            const isCompleted = d.completed
            const isToday = d.is_today

            return (
              <div key={d.day_short || i} className="flex flex-col items-center select-none">
                {/* Circle Status Indicator */}
                <div
                  className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
                    isCompleted
                      ? "bg-accent text-accent-foreground shadow-sm"
                      : isToday
                      ? "border-2 border-accent bg-transparent text-accent"
                      : "bg-secondary/80 text-transparent"
                  }`}
                >
                  {isCompleted && (
                    <Check className="w-3.5 h-3.5 sm:w-4 sm:h-4 stroke-[2.8]" />
                  )}
                </div>

                {/* Day Label */}
                <span
                  className={`font-mono text-[11px] mt-1.5 leading-none tabular-nums ${
                    isToday ? "text-accent font-semibold" : "text-muted-foreground"
                  }`}
                >
                  {d.day_short}
                </span>
              </div>
            )
          })}
        </div>

        {/* Subtitle */}
        <div className="text-xs text-muted-foreground select-none">
          {currentStreak > 0 ? (
            <>
              <strong className="text-foreground font-semibold tabular-nums">
                {currentStreak} dni z rzędu
              </strong>{" "}
              · rekord:{" "}
              <span className="text-foreground font-semibold tabular-nums">
                {maxStreak}
              </span>{" "}
              · śr.{" "}
              <span className="text-foreground font-semibold tabular-nums">
                {avgDailyQuestions}
              </span>{" "}
              pytania/dzień
            </>
          ) : (
            <>
              <strong className="text-foreground font-semibold tabular-nums">
                0 dni z rzędu
              </strong>{" "}
              · Rozpocznij serię dzisiaj!
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
