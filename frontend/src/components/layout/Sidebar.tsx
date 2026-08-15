import { User } from "@/types"
import { Home, BookOpen, BarChart2, CheckSquare, Sun, Moon, Zap, LogOut, LogIn } from "lucide-react"

interface SidebarProps {
  currentTab: string
  onTabChange: (tab: string) => void
  user: User | null
  onOpenAuth: () => void
  onLogout: () => void
  onOpenExam: () => void
  theme: "dark" | "light"
  onToggleTheme: () => void
  streakDays?: number
}

export function Sidebar({
  currentTab,
  onTabChange,
  user,
  onOpenAuth,
  onLogout,
  onOpenExam,
  theme,
  onToggleTheme,
  streakDays = 3,
}: SidebarProps) {
  const tabs = [
    { id: "dashboard", label: "Pulpit", icon: Home },
    { id: "nauka", label: "Nauka", icon: BookOpen },
    { id: "analiza", label: "Analiza", icon: BarChart2 },
    { id: "review", label: "Weryfikacja", icon: CheckSquare },
  ]

  return (
    <aside
      aria-label="Panel boczny nawigacji"
      className="hidden xl:flex fixed top-0 left-0 bottom-0 w-[216px] z-40 bg-card border-r border-border flex-col justify-between p-4 select-none"
    >
      {/* Top Section */}
      <div className="space-y-6">
        {/* Wordmark */}
        <div
          onClick={() => onTabChange("dashboard")}
          className="flex items-center gap-1.5 cursor-pointer px-2 py-1 group"
          title="Przejdź do Pulpitu"
        >
          <span className="font-mono text-sm font-bold tracking-widest text-foreground uppercase">
            PRAWKO<span className="text-accent font-normal">//</span>B
          </span>
        </div>

        {/* Navigation links */}
        <nav className="space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = currentTab === tab.id

            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => onTabChange(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-[8px] text-xs font-mono tracking-wide transition-all ${
                  isActive
                    ? "bg-accent/15 text-accent font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/60 font-medium"
                }`}
              >
                <Icon
                  className={`w-4 h-4 transition-transform ${isActive ? "scale-105" : ""}`}
                  strokeWidth={isActive ? 2.2 : 1.8}
                />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </nav>

        {/* Sprawdzian action trigger */}
        <div className="pt-2">
          <button
            type="button"
            onClick={onOpenExam}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-[8px] bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 transition-colors text-xs font-mono font-semibold"
            title="Sprawdzian Gotowości (32 pytania)"
          >
            <span>Sprawdzian</span>
          </button>
        </div>
      </div>

      {/* Bottom Edge Section */}
      <div className="space-y-3 pt-4 border-t border-border/80">
        {/* Streak */}
        <div
          className="flex items-center justify-between px-2.5 py-1.5 rounded-[8px] bg-secondary/50 border border-border text-xs font-mono"
          title="Dni ciągłej nauki"
        >
          <div className="flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-accent fill-accent" />
            <span className="text-muted-foreground">Ciągłość:</span>
          </div>
          <span className="text-foreground font-bold tabular-nums">{streakDays} dni</span>
        </div>

        {/* User / Auth + Theme */}
        <div className="flex items-center justify-between px-1">
          {user ? (
            <div className="flex items-center gap-2 min-w-0 flex-1 pr-2">
              <span className="text-xs font-mono font-semibold text-foreground truncate" title={user.login}>
                {user.login}
              </span>
              <button
                type="button"
                onClick={onLogout}
                className="text-muted-foreground hover:text-destructive p-1 rounded transition-colors"
                title="Wyloguj"
                aria-label="Wyloguj"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={onOpenAuth}
              className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Zaloguj</span>
            </button>
          )}

          {/* Theme switcher */}
          <button
            type="button"
            onClick={onToggleTheme}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-[6px] hover:bg-secondary transition-colors"
            title={theme === "dark" ? "Przełącz na jasny motyw" : "Przełącz na ciemny motyw"}
            aria-label="Przełącz motyw"
          >
            {theme === "dark" ? (
              <Sun className="w-3.5 h-3.5 text-foreground/80" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-foreground/80" />
            )}
          </button>
        </div>
      </div>
    </aside>
  )
}
