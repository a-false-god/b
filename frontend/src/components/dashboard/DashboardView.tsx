import { useState, useEffect, useCallback } from "react"
import { DashboardData, User } from "@/types"
import { ThetaWidget } from "@/components/dashboard/ThetaWidget"
import { DomainBars } from "@/components/dashboard/DomainBars"
import { CoverageCard } from "@/components/dashboard/CoverageCard"
import { ReasonSplit } from "@/components/dashboard/ReasonSplit"
import { RepeatsDueCard } from "@/components/dashboard/RepeatsDueCard"
import { Loader2 } from "lucide-react"

interface DashboardViewProps {
  user: User | null
  onOpenAuth: () => void
  onNavigateToNauka: () => void
  onOpenExam: () => void
}

export function DashboardView({
  user,
  onNavigateToNauka,
}: DashboardViewProps) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/dashboard", { credentials: "include" })
      if (res.ok) {
        const d: DashboardData = await res.json()
        setData(d)
      } else {
        // Fallback default mock
        setData({
          user: {
            id: 0,
            login: user ? user.login : "Mike",
            skill_theta: 1.45,
            n: 18,
          },
          skill_theta: 1.45,
          per_axis_b: {},
          metrics: {
            total_answers: 18,
            correct_answers: 16,
            accuracy_percent: 88.9,
            mastered_count: 0,
            avg_time_ms: 6500,
          },
          coverage: {
            total_cat_b: 2135,
            never_seen: 2134,
            seen: 1,
            mastered: 0,
          },
          domain_performance: [
            { axis_b: "znaki_i_sygnaly", theta: 1.2, error_count: 0, total_attempts: 8, accuracy_pct: 90 },
            { axis_b: "pierwszenstwo", theta: 0.8, error_count: 1, total_attempts: 6, accuracy_pct: 75 },
            { axis_b: "manewry_i_pozycja", theta: 0.3, error_count: 1, total_attempts: 4, accuracy_pct: 60 },
          ],
          repeats_due: 2,
          reason_split: { slips: 0, mistakes: 2, uncertainty: 0 },
          skill_history: [
            { id: 1, theta: 0.2, created_at: "" },
            { id: 2, theta: 0.5, created_at: "" },
            { id: 3, theta: 0.8, created_at: "" },
            { id: 4, theta: 1.1, created_at: "" },
            { id: 5, theta: 1.45, created_at: "" },
          ],
          hardest_questions: [],
          recent_activity: [],
        })
      }
    } catch {
      console.error("Error fetching dashboard")
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    fetchDashboard()
  }, [fetchDashboard])

  if (loading && !data) {
    return (
      <div className="w-full min-h-[360px] rounded-[12px] border border-border bg-card flex flex-col items-center justify-center text-muted-foreground gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-accent" />
        <span className="text-xs font-mono">Wczytywanie statystyk...</span>
      </div>
    )
  }

  const d = data!
  const userName = user?.login || (d.user?.login && d.user.login !== "Kierowca" ? d.user.login : "Mike")

  return (
    <div className="space-y-2.5 animate-fade-in-up">
      {/* Welcome Title */}
      <div className="pt-0.5 pb-1">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          Witaj, {userName}
        </h1>
      </div>

      {/* 1. Hero Readiness & Progress Widget */}
      <ThetaWidget
        theta={d.skill_theta}
        n={d.metrics.total_answers}
        accuracyPercent={d.metrics.accuracy_percent}
        history={d.skill_history}
        onNavigateToNauka={onNavigateToNauka}
      />

      {/* 2. Repeats Due Card */}
      <RepeatsDueCard
        repeatsDue={d.repeats_due}
        onStartReview={onNavigateToNauka}
      />

      {/* 3. Coverage & Reason Split (2 Columns) */}
      <div className="grid grid-cols-2 gap-2.5">
        <CoverageCard
          total={d.coverage.total_cat_b}
          mastered={d.coverage.mastered}
          seen={d.coverage.seen}
          neverSeen={d.coverage.never_seen}
        />
        <ReasonSplit
          slips={d.reason_split.slips}
          mistakes={d.reason_split.mistakes}
          uncertainty={d.reason_split.uncertainty}
        />
      </div>

      {/* 4. Domain Performance Bars */}
      <DomainBars domains={d.domain_performance} />
    </div>
  )
}
