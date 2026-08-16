import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface TodayCardProps {
  todayAnswers: number
  dailyGoal: number
  repeatsToday: number
  newToday: number
  estMinutes: number
  formattedDate: string
  onStartLearning: () => void
}

export function TodayCard({
  todayAnswers = 8,
  dailyGoal = 20,
  repeatsToday = 6,
  newToday = 12,
  estMinutes = 12,
  formattedDate = "DZISIAJ · NIEDZIELA 16.08",
  onStartLearning,
}: TodayCardProps) {
  const pct = Math.min(100, Math.max(0, (todayAnswers / (dailyGoal || 20)) * 100))

  return (
    <Card className="rounded-[14px] border border-border bg-card shadow-none overflow-hidden">
      <CardContent className="p-4 sm:p-5 space-y-3.5">
        {/* Header Tag */}
        <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground select-none font-medium">
          {formattedDate.toUpperCase()}
        </div>

        {/* Hero Number */}
        <div className="flex items-baseline">
          <span className="text-[38px] sm:text-[42px] font-mono font-bold tracking-tight text-foreground tabular-nums leading-none">
            {todayAnswers}/{dailyGoal}
          </span>
          <span className="text-sm font-sans text-muted-foreground font-normal ml-2.5 select-none">
            pytań
          </span>
        </div>

        {/* Breakdown Subtitle */}
        <div className="text-xs text-muted-foreground select-none">
          {todayAnswers > 0 ? (
            <>
              w tym{" "}
              <strong className="text-foreground font-semibold tabular-nums">
                {repeatsToday} powtórek
              </strong>{" "}
              ·{" "}
              <strong className="text-foreground font-semibold tabular-nums">
                {newToday} nowych
              </strong>{" "}
              ·{" "}
              <strong className="text-foreground font-semibold tabular-nums">
                ~{estMinutes} min
              </strong>
            </>
          ) : (
            <>
              Rozpocznij pierwszą sesję ·{" "}
              <strong className="text-foreground font-semibold tabular-nums">
                {dailyGoal} pytań
              </strong>{" "}
              ·{" "}
              <strong className="text-foreground font-semibold tabular-nums">
                ~{estMinutes} min
              </strong>
            </>
          )}
        </div>

        {/* Progress Bar */}
        <div className="h-2 w-full rounded-full bg-secondary/80 overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Primary CTA Button */}
        <Button
          onClick={onStartLearning}
          className="w-full h-11 mt-1 rounded-[10px] bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center select-none shadow-none font-sans"
        >
          <span className="inline-flex items-center justify-center px-1.5 py-0.5 mr-2 rounded border border-primary-foreground/30 font-mono text-[10px] uppercase font-bold tracking-wider">
            S
          </span>
          <span>{todayAnswers > 0 ? "Kontynuuj naukę" : "Rozpocznij naukę"}</span>
        </Button>
      </CardContent>
    </Card>
  )
}
