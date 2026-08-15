import { User } from "@/types"
import { Sun, Moon, Zap, LogOut } from "lucide-react"

interface HeaderProps {
  user: User | null
  onOpenAuth: () => void
  onLogout: () => void
  onOpenExam: () => void
  theme: "dark" | "light"
  onToggleTheme: () => void
  onLogoClick?: () => void
  streakDays?: number
}

export function Header({
  user,
  onLogout,
  onOpenExam,
  theme,
  onToggleTheme,
  onLogoClick,
  streakDays = 3,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/90 backdrop-blur-md">
      <div className="max-w-[560px] mx-auto px-4 h-11 sm:h-12 flex items-center justify-between gap-3">
        {/* Wordmark: Mono "PRAWKO//B" */}
        <div
          className="flex items-center gap-1.5 cursor-pointer select-none group"
          onClick={onLogoClick}
          title="Przejdź do Pulpitu"
        >
          <span className="font-mono text-xs sm:text-sm font-bold tracking-widest text-foreground whitespace-nowrap uppercase">
            PRAWKO<span className="text-accent font-normal">//</span>B
          </span>
        </div>

        {/* Right: Sprawdzian + Streak + Theme switch */}
        <div className="flex items-center gap-2">
          {/* Sprawdzian button */}
          <button
            onClick={onOpenExam}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-accent/10 border border-accent/30 text-accent text-xs font-mono select-none hover:bg-accent/20 transition-colors"
            title="Sprawdzian Gotowości (32 pytania)"
          >
            <span>Sprawdzian</span>
          </button>

          {/* Streak indicator */}
          <div
            className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-secondary/50 border border-border text-xs font-mono select-none"
            title="Dni ciągłej nauki"
          >
            <Zap className="w-3.5 h-3.5 text-accent fill-accent" />
            <span className="text-muted-foreground">
              <strong className="text-foreground tabular-nums font-semibold">{streakDays}</strong> dni
            </span>
          </div>

          {/* Theme switcher */}
          <button
            onClick={onToggleTheme}
            className="p-1 text-muted-foreground hover:text-foreground rounded-md transition-colors"
            title={theme === "dark" ? "Przełącz na jasny motyw" : "Przełącz na ciemny motyw"}
            aria-label="Przełącz motyw"
          >
            {theme === "dark" ? (
              <Sun className="w-3.5 h-3.5 text-foreground/80" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-foreground/80" />
            )}
          </button>

          {user && (
            <button
              onClick={onLogout}
              className="p-1 text-muted-foreground hover:text-destructive rounded-md transition-colors"
              title="Wyloguj"
              aria-label="Wyloguj"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
