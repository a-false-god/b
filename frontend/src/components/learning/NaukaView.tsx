import { useState, useEffect, useRef, useCallback } from "react"
import { Question, AnswerResponse, User } from "@/types"
import { QuestionCard } from "@/components/learning/QuestionCard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useHotkeys } from "@/hooks/useHotkeys"
import { useTouchSwipe } from "@/hooks/useTouchSwipe"
import { ArrowLeft, ArrowRight, Lightbulb, Loader2, SlidersHorizontal } from "lucide-react"

interface NaukaViewProps {
  user: User | null
  onOpenAuth: (message?: string) => void
  onAnswerSubmitted?: () => void
}

export function NaukaView({ user, onOpenAuth, onAnswerSubmitted }: NaukaViewProps) {
  const [learningMode, setLearningMode] = useState<"auto" | "drill">("auto")
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loading, setLoading] = useState(true)

  // Filters for drill mode
  const [showFilters, setShowFilters] = useState(false)
  const [scopeFilter, setScopeFilter] = useState("")
  const [axisAFilter, setAxisAFilter] = useState("")
  const [axisBFilter, setAxisBFilter] = useState("")
  const [searchQuery, setSearchQuery] = useState("")

  // Answering state
  const [answered, setAnswered] = useState(false)
  const [chosenOption, setChosenOption] = useState<string | null>(null)
  const [answerResult, setAnswerResult] = useState<AnswerResponse | null>(null)
  const [showExplanation, setShowExplanation] = useState(true)

  const startTimeRef = useRef<number>(Date.now())
  const sessionIdRef = useRef<string>("sess_" + Math.random().toString(36).substring(2, 10))

  // Fetch questions
  const loadQuestions = useCallback(async () => {
    setLoading(true)
    try {
      if (learningMode === "auto" && !scopeFilter && !axisAFilter && !axisBFilter && !searchQuery) {
        const res = await fetch("/api/session/next?mode=auto&limit=20", { credentials: "include" })
        if (res.ok) {
          const data = await res.json()
          if (Array.isArray(data) && data.length > 0) {
            setQuestions(data)
            setCurrentIndex(0)
            setAnswered(false)
            setChosenOption(null)
            setAnswerResult(null)
            startTimeRef.current = Date.now()
            setLoading(false)
            return
          }
        }
      }

      // Drill mode or fallback
      const params = new URLSearchParams({ category: "B", limit: "100" })
      if (scopeFilter) params.append("scope", scopeFilter)
      if (axisAFilter) params.append("axisA", axisAFilter)
      if (axisBFilter) params.append("axisB", axisBFilter)
      if (searchQuery) params.append("q", searchQuery)

      const res = await fetch(`/api/questions?${params.toString()}`, { credentials: "include" })
      if (res.ok) {
        const data = await res.json()
        setQuestions(data)
        setCurrentIndex(0)
        setAnswered(false)
        setChosenOption(null)
        setAnswerResult(null)
        startTimeRef.current = Date.now()
      }
    } catch (err) {
      console.error("Failed to load questions", err)
    } finally {
      setLoading(false)
    }
  }, [learningMode, scopeFilter, axisAFilter, axisBFilter, searchQuery])

  useEffect(() => {
    loadQuestions()
  }, [loadQuestions])

  const currentQ = questions[currentIndex]

  // Submit choice
  const handleSelectOption = async (choice: string) => {
    if (answered || !currentQ) return

    if (!user) {
      onOpenAuth("Zaloguj się, aby zapisywać odpowiedzi i budować swoje statystyki.")
      return
    }

    const elapsedMs = Date.now() - startTimeRef.current
    setAnswered(true)
    setChosenOption(choice)

    try {
      const res = await fetch("/api/answers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          question_id: currentQ.id,
          chosen: choice,
          time_ms: elapsedMs,
          session_id: sessionIdRef.current,
        }),
      })

      if (res.status === 401) {
        setAnswered(false)
        onOpenAuth("Sesja wygasła. Zaloguj się ponownie.")
        return
      }

      if (res.ok) {
        const data: AnswerResponse = await res.json()
        setAnswerResult(data)
        if (onAnswerSubmitted) onAnswerSubmitted()
      }
    } catch (err) {
      console.error("Failed to submit answer", err)
    }
  }

  // Navigation handlers
  const handlePrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1)
      setAnswered(false)
      setChosenOption(null)
      setAnswerResult(null)
      startTimeRef.current = Date.now()
    }
  }, [currentIndex])

  const handleNext = useCallback(() => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1)
      setAnswered(false)
      setChosenOption(null)
      setAnswerResult(null)
      startTimeRef.current = Date.now()
    }
  }, [currentIndex, questions.length])

  const handleToggleExplanation = useCallback(() => {
    setShowExplanation((prev) => !prev)
  }, [])

  // Setup hotkeys and touch swipe
  useHotkeys({
    onPrev: handlePrev,
    onNext: handleNext,
    onAnswer: handleSelectOption,
    onToggleExplanation: handleToggleExplanation,
  })

  useTouchSwipe({
    onSwipeLeft: handleNext,
    onSwipeRight: handlePrev,
  })

  const progressPercent = questions.length > 0 ? ((currentIndex + 1) / questions.length) * 100 : 0

  return (
    <div className="space-y-4 animate-fade-in-up pb-8">
      {/* 1. Ritual Session Row: "SESJA" micro-caps + 3px progress track (accent fill) + "1/20" mono */}
      <div className="flex items-center gap-3 px-1 py-1">
        <span className="text-[10px] font-mono font-bold tracking-widest text-muted-foreground uppercase select-none">
          SESJA
        </span>

        <div className="h-[3px] bg-secondary/80 rounded-full overflow-hidden flex-1 relative">
          <div
            className="h-full bg-accent rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold tabular-nums text-foreground/90 select-none">
            {questions.length > 0 ? `${currentIndex + 1}/${questions.length}` : "0/0"}
          </span>

          <button
            onClick={() => setShowFilters((prev) => !prev)}
            className={`p-1 rounded hover:bg-secondary transition-colors ${
              showFilters || learningMode === "drill" ? "text-accent" : "text-muted-foreground"
            }`}
            title="Dostosuj filtry sesji"
            aria-label="Filtry"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Mode / Filters Drawer (Collapsible) */}
      {showFilters && (
        <div className="p-4 rounded-[12px] border border-border bg-card space-y-3 animate-slide-down">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold text-foreground uppercase tracking-wider">
              Tryb nauki
            </span>
            <div className="flex items-center gap-1 bg-secondary/60 p-0.5 rounded-md border border-border">
              <button
                onClick={() => {
                  setLearningMode("auto")
                  setScopeFilter("")
                  setAxisAFilter("")
                  setAxisBFilter("")
                  setSearchQuery("")
                }}
                className={`px-2.5 py-1 text-xs font-mono rounded transition-all ${
                  learningMode === "auto"
                    ? "bg-card text-foreground font-semibold border border-border"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Kompozytor (Auto)
              </button>
              <button
                onClick={() => setLearningMode("drill")}
                className={`px-2.5 py-1 text-xs font-mono rounded transition-all ${
                  learningMode === "drill"
                    ? "bg-card text-foreground font-semibold border border-border"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Filtry (Drill)
              </button>
            </div>
          </div>

          {learningMode === "drill" && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-2 border-t border-border/60">
              <div>
                <label className="text-[10px] font-mono font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
                  Zakres
                </label>
                <select
                  value={scopeFilter}
                  onChange={(e) => setScopeFilter(e.target.value)}
                  className="w-full h-8 text-xs bg-background border border-input rounded-md px-2 text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="">Wszystkie zakresy</option>
                  <option value="PODSTAWOWY">Podstawowy</option>
                  <option value="SPECJALISTYCZNY">Specjalistyczny</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-mono font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
                  Domena (Oś B)
                </label>
                <select
                  value={axisBFilter}
                  onChange={(e) => setAxisBFilter(e.target.value)}
                  className="w-full h-8 text-xs bg-background border border-input rounded-md px-2 text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="">Wszystkie domeny</option>
                  <option value="znaki_i_sygnaly">Znaki i sygnały</option>
                  <option value="pierwszenstwo">Pierwszeństwo</option>
                  <option value="manewry_i_pozycja">Manewry i pozycja</option>
                  <option value="predkosc_i_odleglosci">Prędkość i odstępy</option>
                  <option value="technika_pojazdu">Technika pojazdu</option>
                  <option value="administracja_i_kary">Administracja i kary</option>
                  <option value="pierwsza_pomoc">Pierwsza pomoc</option>
                  <option value="ekologia">Ekologia</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-mono font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
                  Szukaj
                </label>
                <Input
                  type="text"
                  placeholder="Treść pytania..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-8 text-xs font-mono"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. Main Question Card */}
      {loading ? (
        <div className="w-full min-h-[360px] rounded-[12px] border border-border bg-card flex flex-col items-center justify-center text-muted-foreground gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-accent" />
          <span className="text-xs font-mono">Wczytywanie pytania...</span>
        </div>
      ) : currentQ ? (
        <QuestionCard
          question={currentQ}
          index={currentIndex}
          total={questions.length}
          isAutoMode={learningMode === "auto"}
          answered={answered}
          chosenOption={chosenOption}
          answerResult={answerResult}
          showExplanation={showExplanation}
          onSelectOption={handleSelectOption}
        />
      ) : (
        <div className="w-full p-12 rounded-[12px] border border-border bg-card text-center space-y-2">
          <p className="text-sm font-medium text-foreground">Brak pytań spełniających kryteria.</p>
          <p className="text-xs font-mono text-muted-foreground">Zmień filtry lub zresetuj sesję.</p>
        </div>
      )}

      {/* 3. Navigation Controls & Desktop Hotkeys Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
        {/* Hotkey Legend (Desktop only) */}
        <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground select-none">
          <span>Klawisze:</span>
          <kbd className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-[10px]">←</kbd>
          <kbd className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-[10px]">→</kbd>
          <span className="ml-1.5">Wybór:</span>
          <kbd className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-[10px]">T</kbd>
          <kbd className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-[10px]">N</kbd>
          <span>/</span>
          <kbd className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-[10px]">A</kbd>
          <kbd className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-[10px]">B</kbd>
          <kbd className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-[10px]">C</kbd>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          {answered && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleExplanation}
              className="text-xs h-9 gap-1.5 border-border rounded-[8px] font-mono"
              title="Pokaż/ukryj wyjaśnienie (Klawisz E)"
            >
              <Lightbulb className="w-3.5 h-3.5" />
              <span>{showExplanation ? "Ukryj" : "Wyjaśnienie"}</span>
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={handlePrev}
            disabled={currentIndex === 0 || loading}
            className="text-xs h-9 gap-1.5 flex-1 sm:flex-initial border-border rounded-[8px] font-mono"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Poprzednie</span>
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={handleNext}
            disabled={currentIndex >= questions.length - 1 || loading}
            className="text-xs h-9 gap-1.5 flex-1 sm:flex-initial font-semibold bg-primary text-primary-foreground hover:opacity-90 rounded-[8px] font-mono"
          >
            <span>Następne</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}
