import { useState } from "react"
import { Question, AnswerResponse } from "@/types"
import { MediaViewer } from "@/components/media/MediaViewer"
import { AnswerButtons } from "@/components/learning/AnswerButtons"
import { ExplanationCard } from "@/components/learning/ExplanationCard"
import { Info } from "lucide-react"

interface QuestionCardProps {
  question: Question
  index: number
  total: number
  isAutoMode: boolean
  answered: boolean
  chosenOption: string | null
  answerResult: AnswerResponse | null
  showExplanation: boolean
  onSelectOption: (option: string) => void
  disabled?: boolean
  headingRef?: React.RefObject<HTMLHeadingElement>
}

const DOMAIN_LABELS: Record<string, string> = {
  znaki_i_sygnaly: "Znaki i sygnały",
  pierwszenstwo: "Pierwszeństwo",
  manewry_i_pozycja: "Manewry i pozycja",
  predkosc_i_odleglosci: "Prędkość i odstępy",
  technika_pojazdu: "Technika pojazdu",
  administracja_i_kary: "Administracja i kary",
  pierwsza_pomoc: "Pierwsza pomoc",
  ekologia: "Ekologia",
}

export function QuestionCard({
  question,
  answered,
  chosenOption,
  answerResult,
  showExplanation,
  onSelectOption,
  disabled = false,
  headingRef,
}: QuestionCardProps) {
  const [showDebugMeta, setShowDebugMeta] = useState(false)
  const isCorrect = answerResult ? Boolean(answerResult.is_correct) : null
  const correctOption = answerResult
    ? answerResult.correct_answer
    : answered
    ? question.correct
    : null

  // Meta line formatting: "Znaki i sygnały · podstawowy · 3 pkt"
  const domain = question.axis_b ? (DOMAIN_LABELS[question.axis_b] || question.axis_b) : "Wiedza ogólna"
  const scopeText = question.scope ? question.scope.toLowerCase() : "podstawowy"
  const pointsText = `${question.points || 1} pkt`
  const metaLine = `${domain} · ${scopeText} · ${pointsText}`

  // Screen reader polite announcement text (invisible, a11y)
  const announcementText = answered
    ? isCorrect
      ? "Odpowiedź poprawna."
      : `Odpowiedź błędna. Poprawna odpowiedź: ${correctOption === "T" ? "TAK" : correctOption === "N" ? "NIE" : correctOption}.`
    : ""

  return (
    <div className="w-full rounded-[12px] border border-border bg-card p-4 sm:p-6 transition-all">
      {/* Hidden ARIA Live region for screen readers (§6 a11y) */}
      <div aria-live="polite" className="sr-only">
        {announcementText}
      </div>

      {/* 1. Media Container (16:9, radius 12, hairline ring) */}
      <MediaViewer media={question.media} mediaKind={question.media_kind} />

      {/* 2. Question Text as HERO: 23px / weight 700 / letter-spacing -0.015em, left-aligned, 16px below media */}
      <div className="mt-4 max-h-[160px] overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="text-[23px] font-bold tracking-[-0.015em] leading-[1.3] text-foreground text-left focus:outline-none"
        >
          {question.q_pl}
        </h2>

        {/* Meta line directly below question */}
        <p className="text-[12.5px] text-muted-foreground font-normal select-none mt-1.5 text-left">
          {metaLine}
        </p>
      </div>

      {/* 3. Answers: 14px below question container, cards 64px, gap 8px */}
      <div className="mt-3.5">
        <AnswerButtons
          type={question.type}
          aPl={question.a_pl}
          bPl={question.b_pl}
          cPl={question.c_pl}
          answered={answered}
          chosenOption={chosenOption}
          correctOption={correctOption}
          isCorrect={isCorrect}
          onSelect={onSelectOption}
          disabled={disabled}
        />
      </div>

      {/* 4. Explanation Card with verbal verdict in header ("Dobrze." / "Nie tym razem.") */}
      {answered && showExplanation && (
        <div className="mt-3.5">
          <ExplanationCard
            questionId={question.id}
            isCorrect={isCorrect}
            explanation={answerResult?.explanation}
            legalBasis={answerResult?.legal_basis}
            pending={answerResult?.pending_explanation}
          />
        </div>
      )}

      {/* 5. Subtle Debug Affordance */}
      <div className="mt-4 pt-2 flex items-center justify-between text-[11px] font-mono text-faint border-t border-border/40 select-none">
        <button
          type="button"
          onClick={() => setShowDebugMeta((prev) => !prev)}
          className="flex items-center gap-1 hover:text-muted-foreground transition-colors"
          title="Szczegóły techniczne pytania"
        >
          <Info className="w-3 h-3" />
          <span>ID {question.id}</span>
        </button>

        {showDebugMeta && (
          <span className="text-[10px] text-muted-foreground animate-fade-in-up">
            Kat. B • {question.type} • Oś A: {question.axis_a || "n/a"} • Oś B: {question.axis_b || "n/a"}
          </span>
        )}
      </div>
    </div>
  )
}
