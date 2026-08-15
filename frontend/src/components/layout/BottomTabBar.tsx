import { Home, BookOpen, BarChart2, CheckSquare } from "lucide-react"

interface BottomTabBarProps {
  currentTab: string
  onTabChange: (tab: string) => void
}

export function BottomTabBar({ currentTab, onTabChange }: BottomTabBarProps) {
  const tabs = [
    { id: "dashboard", label: "PULPIT", icon: Home },
    { id: "nauka", label: "NAUKA", icon: BookOpen },
    { id: "analiza", label: "ANALIZA", icon: BarChart2 },
    { id: "review", label: "WERYFIKACJA", icon: CheckSquare },
  ]

  return (
    <nav
      aria-label="Główna nawigacja"
      className="fixed bottom-3 sm:bottom-4 left-1/2 -translate-x-1/2 w-[calc(100%-1.5rem)] max-w-[480px] z-50 rounded-[18px] bg-card/95 backdrop-blur-md tab-bar-shadow border border-border px-1.5 py-1.5 flex items-center justify-between transition-all xl:hidden"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon
        const isActive = currentTab === tab.id

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 flex flex-col items-center justify-center py-1.5 px-1 rounded-[8px] transition-all duration-150 select-none ${
              isActive
                ? "bg-accent/15 text-accent font-semibold"
                : "text-muted-foreground hover:text-foreground active:scale-95"
            }`}
          >
            <Icon
              className={`w-4 h-4 transition-transform ${isActive ? "scale-105" : ""}`}
              strokeWidth={isActive ? 2.2 : 1.8}
            />
            <span className="text-[8px] font-mono tracking-wider mt-0.5 leading-none font-bold">
              {tab.label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
