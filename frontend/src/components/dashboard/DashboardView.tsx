import { useState, useEffect, useCallback } from "react"
import { DashboardData, User } from "@/types"
import { TodayCard } from "@/components/dashboard/TodayCard"
import { ExamReadinessCard } from "@/components/dashboard/ExamReadinessCard"
import { WeeklyStreakCard } from "@/components/dashboard/WeeklyStreakCard"
import { WeakPointsCard } from "@/components/dashboard/WeakPointsCard"
import { Loader2 } from "lucide-react"

interface DashboardViewProps {
  user: User | null
  onOpenAuth: () => void
  onNavigateToNauka: (filter?: { axisB?: string }) => void
  onOpenExam: () => void
}

export function DashboardView({
  user,
  onNavigateToNauka,
  onOpenExam,
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
        // Fallback mock strictly conforming to V3 specs
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
            { axis_b: "znaki_i_sygnaly", theta: 1.2, error_count: 0, total_attempts: 8, accuracy_pct: 62 },
            { axis_b: "administracja_i_kary", theta: 0.8, error_count: 1, total_attempts: 6, accuracy_pct: 48 },
            { axis_b: "technika_pojazdu", theta: 0.3, error_count: 1, total_attempts: 4, accuracy_pct: 71 },
          ],
          repeats_due: 6,
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
          today: {
            today_answers: 8,
            daily_goal: 20,
            repeats_today: 6,
            new_today: 12,
            est_minutes: 12,
            formatted_date: "DZISIAJ · NIEDZIELA 16.08",
          },
          readiness: {
            score: 61,
            max_score: 74,
            pass_threshold: 68,
            score_delta: 6,
            points_needed: 7,
            exams_this_week: 3,
          },
          streak: {
            current_streak: 4,
            max_streak: 6,
            avg_daily_questions: 22,
            week_days: [
              { day_short: "pn", date: "2026-08-10", completed: true, is_today: false, is_future: false, answers_count: 24 },
              { day_short: "wt", date: "2026-08-11", completed: true, is_today: false, is_future: false, answers_count: 20 },
              { day_short: "śr", date: "2026-08-12", completed: true, is_today: false, is_future: false, answers_count: 30 },
              { day_short: "cz", date: "2026-08-13", completed: true, is_today: false, is_future: false, answers_count: 22 },
              { day_short: "pt", date: "2026-08-14", completed: false, is_today: false, is_future: false, answers_count: 0 },
              { day_short: "so", date: "2026-08-15", completed: false, is_today: false, is_future: false, answers_count: 0 },
              { day_short: "nd", date: "2026-08-16", completed: false, is_today: true, is_future: false, answers_count: 8 },
            ],
          },
          weak_points: [
            { axis_b: "znaki_i_sygnaly", label: "znaki i sygnały", accuracy_pct: 62, error_count: 3, theta: 0.4 },
            { axis_b: "administracja_i_kary", label: "przepisy ruchu", accuracy_pct: 48, error_count: 5, theta: 0.1 },
            { axis_b: "technika_pojazdu", label: "obsługa pojazdu", accuracy_pct: 71, error_count: 2, theta: 0.6 },
          ],
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

  // Global shortcut 'S' / 's' to trigger learning session
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === "input" || tag === "textarea" || tag === "select") return
      if (e.key === "s" || e.key === "S") {
        e.preventDefault()
        onNavigateToNauka()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onNavigateToNauka])

  if (loading && !data) {
    return (
      <div className="w-full min-h-[360px] rounded-[14px] border border-border bg-card flex flex-col items-center justify-center text-muted-foreground gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-accent" />
        <span className="text-xs font-mono">Wczytywanie statystyk...</span>
      </div>
    )
  }

  const d = data!

  return (
    <div className="space-y-3 sm:space-y-3.5 animate-fade-in-up">
      {/* 1. Daily Learning Progress Card */}
      <TodayCard
        todayAnswers={d.today?.today_answers ?? 8}
        dailyGoal={d.today?.daily_goal ?? 20}
        repeatsToday={d.today?.repeats_today ?? d.repeats_due ?? 6}
        newToday={d.today?.new_today ?? 12}
        estMinutes={d.today?.est_minutes ?? 12}
        formattedDate={d.today?.formatted_date ?? "DZISIAJ · NIEDZIELA 16.08"}
        onStartLearning={() => onNavigateToNauka()}
      />

      {/* 2. Exam Readiness Card */}
      <ExamReadinessCard
        score={d.readiness?.score ?? 61}
        maxScore={d.readiness?.max_score ?? 74}
        passThreshold={d.readiness?.pass_threshold ?? 68}
        scoreDelta={d.readiness?.score_delta ?? 6}
        pointsNeeded={d.readiness?.points_needed ?? 7}
        examsThisWeek={d.readiness?.exams_this_week ?? 3}
        onOpenExam={onOpenExam}
      />

      {/* 3. Weekly Consistency & Streak Card */}
      <WeeklyStreakCard
        currentStreak={d.streak?.current_streak ?? 4}
        maxStreak={d.streak?.max_streak ?? 6}
        avgDailyQuestions={d.streak?.avg_daily_questions ?? 22}
        weekDays={d.streak?.week_days}
      />

      {/* 4. Weak Points Card (Tap to Filtered Session) */}
      <WeakPointsCard
        weakPoints={d.weak_points}
        onSelectDomain={(axisB) => onNavigateToNauka({ axisB })}
      />
    </div>
  )
}

