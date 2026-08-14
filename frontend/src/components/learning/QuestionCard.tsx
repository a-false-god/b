import { useState } from "react"
import { Question, AnswerResponse } from "@/types"
import { MediaViewer } from "@/components/media/MediaViewer"
import { AnswerButtons } from "@/components/learning/AnswerButtons"
import { ExplanationCard } from "@/components/learning/ExplanationCard"
import { CheckCircle2, XCircle, Info } from "lucide-react"

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

  return (
    <div className="w-full rounded-[12px] border border-border bg-card p-4 sm:p-6 space-y-4 transition-all">
      {/* 1. Media Container (16:9, radius 12, hairline ring, no chips overlaid) */}
      <MediaViewer media={question.media} mediaKind={question.media_kind} />

      {/* 2. Question Text as HERO (23px bold, tracking -0.015em) */}
      <div className="space-y-1.5 pt-1">
        <h2 className="text-[20px] sm:text-[23px] font-bold tracking-[-0.015em] leading-[1.3] text-foreground">
          {question.q_pl}
        </h2>

        {/* Meta line directly below question */}
        <p className="text-[12.5px] text-muted-foreground font-normal select-none">
          {metaLine}
        </p>
      </div>

      {/* 3. Answers (min 64px, radius 12, 1.5px border, 30px radius 8 key badge) */}
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

      {/* 4. Instant Answer Feedback Banner */}
      {answered && answerResult && (
        <div
          className={`flex items-center gap-2.5 p-3.5 rounded-[12px] border text-xs sm:text-sm font-semibold animate-confirm-pop select-none ${
            isCorrect
              ? "bg-success/15 border-success/40 text-foreground"
              : "bg-destructive/15 border-destructive/40 text-foreground"
          }`}
        >
          {isCorrect ? (
            <>
              <CheckCircle2 className="w-4 h-4 shrink-0 text-success" />
              <span>
                Poprawna odpowiedź! <span className="font-mono text-muted-foreground font-normal">(+{question.points} pkt)</span>
              </span>
            </>
          ) : (
            <>
              <XCircle className="w-4 h-4 shrink-0 text-destructive" />
              <span>
                Błędna odpowiedź. Poprawna to:{" "}
                <strong className="font-mono font-bold underline underline-offset-2">
                  {correctOption}
                </strong>
              </span>
            </>
          )}
        </div>
      )}

      {/* 5. Explanation Card */}
      {answered && showExplanation && (
        <ExplanationCard
          questionId={question.id}
          explanation={answerResult?.explanation}
          legalBasis={answerResult?.legal_basis}
          pending={answerResult?.pending_explanation}
        />
      )}

      {/* 6. Subtle Debug Affordance (Non-persistent chrome) */}
      <div className="pt-2 flex items-center justify-between text-[11px] font-mono text-muted-foreground/60 border-t border-border/40 select-none">
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
