import { useState, useEffect } from "react"
import { useLocation } from "wouter"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { User } from "@/types"
import { Header } from "@/components/layout/Header"
import { Sidebar } from "@/components/layout/Sidebar"
import { BottomTabBar } from "@/components/layout/BottomTabBar"
import { AuthModal } from "@/components/layout/AuthModal"
import { DashboardView } from "@/components/dashboard/DashboardView"
import { NaukaView } from "@/components/learning/NaukaView"
import { AnalyticsView } from "@/components/analytics/AnalyticsView"
import { ReviewQueueView } from "@/components/review/ReviewQueueView"
import { ExamDialog } from "@/components/exam/ExamDialog"
import { ErrorBoundary } from "@/components/common/ErrorBoundary"
import { ToastProvider } from "@/components/ui/toast"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 30, // 30 seconds
    },
  },
})

export function App() {
  const [location, setLocation] = useLocation()
  const [user, setUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem("prawko_user")
      if (saved) return JSON.parse(saved)
    } catch {
      // ignore
    }
    return null
  })
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authMessage, setAuthMessage] = useState<string | undefined>(undefined)
  const [examOpen, setExamOpen] = useState(false)
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try {
      const saved = localStorage.getItem("prawko_theme")
      if (saved === "light" || saved === "dark") return saved
    } catch {
      // ignore
    }
    return "dark"
  })

  // Sync theme to root html element
  useEffect(() => {
    const root = document.documentElement
    if (theme === "dark") {
      root.classList.add("dark")
      root.classList.remove("light")
    } else {
      root.classList.remove("dark")
      root.classList.add("light")
    }
    try {
      localStorage.setItem("prawko_theme", theme)
    } catch {
      // ignore
    }
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"))
  }

  const handleLogout = async () => {
    try {
      await fetch("/auth/logout", {
        method: "POST",
        credentials: "include",
      })
    } catch {
      // ignore
    }
    setUser(null)
    localStorage.removeItem("prawko_user")
  }

  const handleOpenAuth = (msg?: string) => {
    setAuthMessage(msg)
    setAuthModalOpen(true)
  }

  // Derive current tab from wouter location
  const currentTab =
    location === "/nauka"
      ? "nauka"
      : location === "/analiza"
      ? "analiza"
      : location === "/review"
      ? "review"
      : "dashboard"

  const handleTabChange = (tab: string) => {
    if (tab === "dashboard") setLocation("/")
    else setLocation(`/${tab}`)
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <div className="min-h-screen flex flex-col bg-background text-foreground ambient-shell selection:bg-accent selection:text-accent-foreground">
          {/* Desktop Fixed Left Sidebar (≥1200px) */}
          <Sidebar
            currentTab={currentTab}
            onTabChange={handleTabChange}
            user={user}
            onOpenAuth={() => handleOpenAuth()}
            onLogout={handleLogout}
            onOpenExam={() => setExamOpen(true)}
            theme={theme}
            onToggleTheme={toggleTheme}
            streakDays={3}
          />

          {/* Minimal Mobile/Tablet Header (<1200px) */}
          <Header
            user={user}
            onOpenAuth={() => handleOpenAuth()}
            onLogout={handleLogout}
            onOpenExam={() => setExamOpen(true)}
            theme={theme}
            onToggleTheme={toggleTheme}
            onLogoClick={() => handleTabChange("dashboard")}
            streakDays={3}
          />

          {/* Main Content Area — Centered 480–540px column (offset by sidebar on desktop) */}
          <main className="flex-1 w-full max-w-[540px] mx-auto xl:max-w-[756px] xl:pl-[216px] px-3.5 sm:px-4 py-2 sm:py-3 pb-20 sm:pb-24 xl:pb-8">
            <div className="w-full max-w-[540px] mx-auto">
              <ErrorBoundary>
                {currentTab === "dashboard" && (
                  <DashboardView
                    user={user}
                    onOpenAuth={() => handleOpenAuth()}
                    onNavigateToNauka={() => handleTabChange("nauka")}
                    onOpenExam={() => setExamOpen(true)}
                  />
                )}

                {currentTab === "nauka" && (
                  <NaukaView
                    user={user}
                    onOpenAuth={handleOpenAuth}
                    onAnswerSubmitted={() => queryClient.invalidateQueries({ queryKey: ["dashboard"] })}
                  />
                )}

                {currentTab === "analiza" && (
                  <AnalyticsView
                    user={user}
                    onOpenAuth={() => handleOpenAuth()}
                  />
                )}

                {currentTab === "review" && <ReviewQueueView />}
              </ErrorBoundary>
            </div>
          </main>

          {/* Floating Bottom Tab Bar (<1200px, hidden during exam takeover) */}
          {!examOpen && (
            <BottomTabBar
              currentTab={currentTab}
              onTabChange={handleTabChange}
            />
          )}

          {/* Auth Modal */}
          <AuthModal
            open={authModalOpen}
            onOpenChange={setAuthModalOpen}
            onSuccess={(u) => setUser(u)}
            initialMessage={authMessage}
          />

          {/* Fullscreen Exam Check Modal */}
          <ExamDialog
            open={examOpen}
            onOpenChange={setExamOpen}
            onExamFinished={() => queryClient.invalidateQueries({ queryKey: ["dashboard"] })}
          />
        </div>
      </ToastProvider>
    </QueryClientProvider>
  )
}

export default App
