import { Card, CardContent } from "@/components/ui/card"

interface DomainItem {
  axis_b: string
  theta: number
  error_count: number
  total_attempts: number
  accuracy_pct: number
}

interface DomainBarsProps {
  domains: DomainItem[]
}

const DOMAIN_LABELS: Record<string, string> = {
  znaki_i_sygnaly: "Znaki i sygnały",
  pierwszenstwo: "Pierwszeństwo",
  manewry_i_pozycja: "Manewry i pozycja",
  predkosc_i_odleglosci: "Prędkość i odstępy",
  technika_pojazdu: "Technika pojazdu",
  administracja_i_kary: "Przepisy i kary",
  pierwsza_pomoc: "Pierwsza pomoc",
  ekologia: "Ekologia",
}

const DEFAULT_DOMAINS: DomainItem[] = [
  { axis_b: "znaki_i_sygnaly", theta: 1.2, error_count: 0, total_attempts: 8, accuracy_pct: 90 },
  { axis_b: "pierwszenstwo", theta: 0.8, error_count: 1, total_attempts: 6, accuracy_pct: 75 },
  { axis_b: "manewry_i_pozycja", theta: 0.3, error_count: 1, total_attempts: 4, accuracy_pct: 60 },
]

export function DomainBars({ domains }: DomainBarsProps) {
  const displayDomains =
    domains && domains.length > 0 ? domains.slice(0, 5) : DEFAULT_DOMAINS

  return (
    <Card className="rounded-[12px] border border-border bg-card">
      <CardContent className="p-3.5 sm:p-4 space-y-3">
        <div className="text-xs text-muted-foreground font-medium select-none">
          Umiejętność wg domen
        </div>

        <div className="space-y-2.5 pt-0.5">
          {displayDomains.map((d) => {
            const label = DOMAIN_LABELS[d.axis_b] || d.axis_b
            const formattedTheta = `θ ${d.theta >= 0 ? "+" : ""}${d.theta.toFixed(2).replace(".", ",")}`
            // Bar width from theta or accuracy
            const widthPct = Math.max(10, Math.min(100, (d.theta + 2) * 25))

            return (
              <div key={d.axis_b} className="space-y-1.5 select-none">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-normal text-foreground truncate pr-2">
                    {label}
                  </span>
                  <span className="font-mono text-[11px] text-muted-foreground shrink-0 tabular-nums">
                    {formattedTheta}
                  </span>
                </div>

                {/* Visible track + Accent fill */}
                <div className="h-1.5 w-full rounded-full bg-secondary/80 overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-300"
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
