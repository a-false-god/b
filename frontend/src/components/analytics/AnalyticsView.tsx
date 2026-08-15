import { useState, useEffect, useCallback } from "react"
import {
  User,
  AnalyticsCoverage,
  AnalyticsReason,
  AnalyticsHesitation,
  AnalyticsAxisItem,
  AnalyticsOptionItem,
  AnalyticsHardestItem,
} from "@/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { BarChart3, Clock, Shuffle, Flame, Loader2, Zap, AlertTriangle, HelpCircle } from "lucide-react"
import { formatCount } from "@/lib/utils"

interface AnalyticsViewProps {
  user: User | null
  onOpenAuth: () => void
}

export function AnalyticsView({ user, onOpenAuth }: AnalyticsViewProps) {
  const [loading, setLoading] = useState(true)
  const [coverage, setCoverage] = useState<AnalyticsCoverage | null>(null)
  const [reason, setReason] = useState<AnalyticsReason | null>(null)
  const [hesitation, setHesitation] = useState<AnalyticsHesitation[]>([])
  const [axisA, setAxisA] = useState<AnalyticsAxisItem[]>([])
  const [options, setOptions] = useState<AnalyticsOptionItem[]>([])
  const [hardest, setHardest] = useState<AnalyticsHardestItem[]>([])

  const loadAnalytics = useCallback(async () => {
    if (!user) {
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const [covRes, reasonRes, hesRes, axisARes, optRes, hardRes] = await Promise.all([
        fetch("/api/analytics/coverage", { credentials: "include" }),
        fetch("/api/analytics/reason", { credentials: "include" }),
        fetch("/api/analytics/hesitation", { credentials: "include" }),
        fetch("/api/analytics/errors?by=axisA", { credentials: "include" }),
        fetch("/api/analytics/errors?by=option", { credentials: "include" }),
        fetch("/api/analytics/errors?by=question", { credentials: "include" }),
      ])

      if (covRes.ok) setCoverage(await covRes.json())
      if (reasonRes.ok) setReason(await reasonRes.json())
      if (hesRes.ok) {
        const d = await hesRes.json()
        setHesitation(d.hesitation_candidates || [])
      }
      if (axisARes.ok) {
        const d = await axisARes.json()
        setAxisA(d.data || [])
      }
      if (optRes.ok) {
        const d = await optRes.json()
        setOptions(d.data || [])
      }
      if (hardRes.ok) {
        const d = await hardRes.json()
        setHardest(d.data || [])
      }
    } catch {
      console.error("Failed to load analytics")
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    loadAnalytics()
  }, [loadAnalytics])

  if (!user) {
    return (
      <Card className="rounded-[12px] border border-border bg-card text-center p-8 sm:p-12 my-6 animate-fade-in-up">
        <CardContent className="space-y-3">
          <BarChart3 className="w-8 h-8 text-muted-foreground mx-auto opacity-50" />
          <h2 className="text-lg font-bold text-foreground">Panel Analizy Błędów</h2>
          <p className="text-xs text-muted-foreground max-w-md mx-auto font-mono">
            Zaloguj się, aby odblokować 6 wskaźników analitycznych (pokrycie, typy pomyłek, mylone opcje, wahania).
          </p>
          <Button onClick={onOpenAuth} className="mt-2 text-xs font-semibold bg-primary text-primary-foreground hover:opacity-90 rounded-[8px] font-mono">
            Zaloguj się
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <div className="w-full min-h-[360px] rounded-[12px] border border-border bg-card flex flex-col items-center justify-center text-muted-foreground gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-accent" />
        <span className="text-xs font-mono">Wczytywanie analityki...</span>
      </div>
    )
  }

  const covTotal = coverage?.total_cat_b || 2135
  const covMastered = coverage?.mastered || 0
  const covSeen = coverage?.seen || 0
  const covNever = coverage?.never_seen || 2135
  const pctMastered = Math.round((covMastered / covTotal) * 100)
  const pctSeen = Math.round((covSeen / covTotal) * 100)

  return (
    <div className="space-y-4 animate-fade-in-up pb-8">
      {/* Header */}
      <div className="p-4 sm:p-5 rounded-[12px] border border-border bg-card">
        <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-accent" />
          <span>Panel Analizy Błędów</span>
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5 font-mono select-none">
          Profil analityczny: <strong className="text-foreground">{user.login}</strong>
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. Coverage Split */}
        <Card className="rounded-[12px] border border-border bg-card">
          <CardContent className="p-5 space-y-3.5">
            <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground select-none">
              1. Pokrycie Bazy (Coverage)
            </div>
            <div className="h-2 w-full rounded-full bg-secondary flex overflow-hidden p-0.5 gap-0.5">
              <div className="bg-success rounded-l-full" style={{ width: `${pctMastered}%` }} />
              <div className="bg-accent" style={{ width: `${Math.max(0, pctSeen - pctMastered)}%` }} />
              <div className="bg-muted-foreground/30 rounded-r-full" style={{ width: `${Math.max(0, 100 - pctSeen)}%` }} />
            </div>
            <div className="flex items-center justify-between text-xs font-mono text-muted-foreground pt-1 select-none">
              <span>Opanowane: <strong className="text-foreground tabular-nums">{formatCount(covMastered)}</strong></span>
              <span>Widziane: <strong className="text-foreground tabular-nums">{formatCount(covSeen)}</strong></span>
              <span>Niewidziane: <strong className="text-muted-foreground tabular-nums">{formatCount(covNever)}</strong></span>
            </div>
          </CardContent>
        </Card>

        {/* 2. Reason Split */}
        <Card className="rounded-[12px] border border-border bg-card">
          <CardContent className="p-5 space-y-3.5">
            <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground select-none">
              2. Typologia Błędów (Reason)
            </div>
            <div className="grid grid-cols-3 gap-2 font-mono text-xs select-none">
              <div className="p-2 rounded-[8px] bg-secondary/30 border border-border">
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Zap className="w-3 h-3 text-accent" /> Slips (&lt;8s)
                </span>
                <strong className="text-lg text-foreground tabular-nums block mt-1">{formatCount(reason?.slips || 0)}</strong>
              </div>
              <div className="p-2 rounded-[8px] bg-secondary/30 border border-border">
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-destructive" /> Mistakes
                </span>
                <strong className="text-lg text-destructive tabular-nums block mt-1">{formatCount(reason?.mistakes || 0)}</strong>
              </div>
              <div className="p-2 rounded-[8px] bg-secondary/30 border border-border">
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <HelpCircle className="w-3 h-3 text-accent" /> Uncertainty
                </span>
                <strong className="text-lg text-accent tabular-nums block mt-1">{formatCount(reason?.uncertainty || 0)}</strong>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 3. Errors per Axis A */}
        <Card className="rounded-[12px] border border-border bg-card">
          <CardContent className="p-5 space-y-3.5">
            <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground select-none">
              3. Błędy wg Osi Poznawczej (Oś A)
            </div>
            <div className="divide-y divide-border/60">
              {axisA.length === 0 ? (
                <p className="text-xs font-mono text-muted-foreground py-2 select-none">Brak błędów w bazie.</p>
              ) : (
                axisA.map((item) => (
                  <div key={item.axis_value} className="py-2 flex items-center justify-between text-xs">
                    <span className="font-medium text-foreground capitalize">{item.axis_value}</span>
                    <Badge variant="destructive" className="tabular-nums font-mono rounded-[4px]">
                      {formatCount(item.error_count)} błędów
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* 4. Confused Options ABC */}
        <Card className="rounded-[12px] border border-border bg-card">
          <CardContent className="p-5 space-y-3.5">
            <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-1 select-none">
              <Shuffle className="w-3 h-3 text-accent" />
              <span>4. Mylone Opcje (ABC)</span>
            </div>
            <div className="divide-y divide-border/60">
              {options.length === 0 ? (
                <p className="text-xs font-mono text-muted-foreground py-2 select-none">Brak danych o mylonych opcjach.</p>
              ) : (
                options.slice(0, 5).map((opt, i) => (
                  <div key={i} className="py-2 flex items-center justify-between text-xs">
                    <span className="font-mono text-foreground font-semibold">#{opt.question_id}</span>
                    <div className="flex items-center gap-2 font-mono text-[11px] select-none">
                      <span className="text-destructive">Odp: {opt.chosen}</span>
                      <span>→</span>
                      <span className="text-success">Popr: {opt.correct_option}</span>
                      <Badge variant="outline" className="tabular-nums text-[10px] ml-1 rounded-[4px]">
                        {formatCount(opt.confused_count)}x
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* 5. Hesitation Candidates */}
        <Card className="rounded-[12px] border border-border bg-card">
          <CardContent className="p-5 space-y-3.5">
            <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-1 select-none">
              <Clock className="w-3 h-3 text-accent" />
              <span>5. Wahania (&gt;15s)</span>
            </div>
            <div className="divide-y divide-border/60">
              {hesitation.length === 0 ? (
                <p className="text-xs font-mono text-muted-foreground py-2 select-none">Brak pytań z wysokim czasem wahania.</p>
              ) : (
                hesitation.slice(0, 5).map((h, i) => (
                  <div key={i} className="py-2 space-y-0.5 text-xs">
                    <div className="flex items-center justify-between font-mono select-none">
                      <span className="font-semibold text-foreground">#{h.question_id}</span>
                      <span className="text-accent tabular-nums">{(h.time_ms / 1000).toFixed(1)}s</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">{h.q_pl}</p>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* 6. Hardest Questions */}
        <Card className="rounded-[12px] border border-border bg-card">
          <CardContent className="p-5 space-y-3.5">
            <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-1 select-none">
              <Flame className="w-3 h-3 text-destructive" />
              <span>6. Najtrudniejsze Pytania</span>
            </div>
            <div className="divide-y divide-border/60">
              {hardest.length === 0 ? (
                <p className="text-xs font-mono text-muted-foreground py-2 select-none">Brak zarejestrowanych błędów.</p>
              ) : (
                hardest.slice(0, 5).map((q, i) => (
                  <div key={i} className="py-2 space-y-0.5 text-xs">
                    <div className="flex items-center justify-between font-mono select-none">
                      <span className="font-semibold text-foreground">#{q.question_id}</span>
                      <Badge variant="destructive" className="tabular-nums text-[10px] rounded-[4px]">
                        {formatCount(q.error_count)} błędów
                      </Badge>
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">{q.q_pl}</p>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
