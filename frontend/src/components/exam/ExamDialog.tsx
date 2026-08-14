import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MediaViewer } from "@/components/media/MediaViewer"
import { Question, ExamSubmissionResponse } from "@/types"
import { Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react"

interface ExamDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onExamFinished?: () => void
}

interface ExamAnswer {
  question_id: number
  chosen: string
  time_ms: number
}

const TOTAL_EXAM_TIME_SEC = 25 * 60 // 25 minutes

export function ExamDialog({
  open,
  onOpenChange,
  onExamFinished,
}: ExamDialogProps) {
  const [loading, setLoading] = useState(false)
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<ExamAnswer[]>([])
  const [remainingSeconds, setRemainingSeconds] = useState(TOTAL_EXAM_TIME_SEC)
  const [submitting, setSubmitting] = useState(false)
  const [report, setReport] = useState<ExamSubmissionResponse | null>(null)

  // Start exam
  useEffect(() => {
    if (!open) {
      setReport(null)
      setQuestions([])
      setAnswers([])
      return
    }

    const start = async () => {
      setLoading(true)
      try {
        const res = await fetch("/api/exam/start", {
          method: "POST",
          credentials: "include",
        })
        if (res.ok) {
          const data = await res.json()
          setQuestions(data.questions || [])
          setCurrentIndex(0)
          setAnswers([])
          setRemainingSeconds(TOTAL_EXAM_TIME_SEC)
          setReport(null)
        }
      } catch (err) {
        console.error("Failed to start exam", err)
      } finally {
        setLoading(false)
      }
    }

    start()
  }, [open])

  // Timer tick
  useEffect(() => {
    if (!open || report || loading || questions.length === 0) return

    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          handleFinishExam()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [open, report, loading, questions.length, answers])

  const currentQ = questions[currentIndex]

  const handleSelectAnswer = (chosen: string) => {
    if (!currentQ) return

    const updatedAnswers = [
      ...answers,
      {
        question_id: currentQ.id,
        chosen: chosen,
        time_ms: 0,
      },
    ]
    setAnswers(updatedAnswers)

    if (currentIndex + 1 < questions.length) {
      setCurrentIndex((prev) => prev + 1)
    } else {
      handleFinishExam(updatedAnswers)
    }
  }

  const handleFinishExam = async (finalAnswers = answers) => {
    if (submitting) return
    setSubmitting(true)
    const elapsedSec = TOTAL_EXAM_TIME_SEC - remainingSeconds

    try {
      const res = await fetch("/api/exam/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          answers: finalAnswers,
          time_seconds: Math.max(1, elapsedSec),
        }),
      })

      if (res.ok) {
        const data: ExamSubmissionResponse = await res.json()
        setReport(data)
        if (onExamFinished) onExamFinished()
      }
    } catch (err) {
      console.error("Failed to submit exam", err)
    } finally {
      setSubmitting(false)
    }
  }

  const formatTimer = (sec: number) => {
    const mins = Math.floor(sec / 60)
    const s = sec % 60
    return `${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  }

  const isTimeCritical = remainingSeconds < 5 * 60 // < 5:00

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[580px] max-h-[92vh] overflow-y-auto p-5 sm:p-6 rounded-[12px] border border-border bg-card modal-shadow">
        <DialogHeader className="border-b border-border pb-3.5">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-base sm:text-lg font-bold flex items-center gap-2 text-foreground">
              <span>Sprawdzian Gotowości</span>
            </DialogTitle>

            {!report && questions.length > 0 && (
              <div
                className={`flex items-center gap-1.5 px-3 py-1 rounded-[8px] font-mono text-base font-bold tabular-nums border select-none ${
                  isTimeCritical
                    ? "bg-destructive/15 text-destructive border-destructive/40 animate-pulse"
                    : "bg-secondary text-foreground border-border"
                }`}
              >
                <Clock className="w-4 h-4" />
                <span>{formatTimer(remainingSeconds)}</span>
              </div>
            )}
          </div>
        </DialogHeader>

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center text-muted-foreground gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-accent" />
            <span className="text-xs font-mono">Generowanie arkusza 32 pytań...</span>
          </div>
        ) : report ? (
          /* Final Report */
          <div className="py-5 text-center space-y-4 animate-slide-down">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full mx-auto bg-secondary border border-border">
              {report.passed ? (
                <CheckCircle2 className="w-8 h-8 text-success" />
              ) : (
                <XCircle className="w-8 h-8 text-destructive" />
              )}
            </div>

            <div>
              <h2 className="text-xl sm:text-2xl font-bold">
                {report.passed ? (
                  <span className="text-success">WYNIK POZYTYWNY</span>
                ) : (
                  <span className="text-destructive">WYNIK NEGATYWNY</span>
                )}
              </h2>
              <p className="text-xs text-muted-foreground mt-1 font-mono select-none">
                Próg zdawalności: 68 / 74 punktów
              </p>
            </div>

            <div className="p-4 rounded-[12px] border border-border bg-secondary/30 max-w-sm mx-auto">
              <div className="text-4xl font-mono font-bold text-foreground tabular-nums">
                {report.score} <span className="text-base font-normal text-muted-foreground font-mono">/ {report.max_score} PKT</span>
              </div>
              <div className="text-xs font-mono text-muted-foreground mt-2.5 grid grid-cols-2 gap-2 pt-2.5 border-t border-border select-none">
                <div>
                  Poprawnych: <strong className="text-foreground">{report.correct_count} / {report.total_questions}</strong>
                </div>
                <div>
                  Czas: <strong className="text-foreground">{Math.floor(report.time_seconds / 60)}m {report.time_seconds % 60}s</strong>
                </div>
              </div>
            </div>

            <Button
              onClick={() => onOpenChange(false)}
              className="w-full max-w-xs mx-auto font-semibold bg-primary text-primary-foreground hover:opacity-90 rounded-[8px] font-mono"
            >
              Zamknij i wróć do Pulpitu
            </Button>
          </div>
        ) : submitting ? (
          <div className="py-16 flex flex-col items-center justify-center text-muted-foreground gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-accent" />
            <span className="text-xs font-mono">Podliczanie wyników egzaminu...</span>
          </div>
        ) : currentQ ? (
          /* Question Exam Card */
          <div className="space-y-4 py-2">
            {/* Meta bar */}
            <div className="flex items-center justify-between text-xs font-mono select-none">
              <div className="flex items-center gap-1.5">
                <Badge variant="outline" className="rounded-[4px]">{currentQ.scope}</Badge>
                <Badge variant={currentQ.points === 3 ? "pts3" : "outline"} className="tabular-nums font-bold rounded-[4px]">
                  {currentQ.points} PKT
                </Badge>
              </div>
              <span className="text-muted-foreground text-[11px] tabular-nums">
                {currentIndex + 1} / {questions.length}
              </span>
            </div>

            {/* Media */}
            <MediaViewer media={currentQ.media} mediaKind={currentQ.media_kind} />

            {/* Question Text */}
            <h3 className="text-base sm:text-lg font-bold leading-snug text-foreground">
              {currentQ.q_pl}
            </h3>

            {/* Answer Options (min 64px, 12px radius, 1.5px border, 30px key badges) */}
            <div className="grid gap-2.5 pt-1">
              {currentQ.type === "TN" ? (
                <>
                  <button
                    type="button"
                    onClick={() => handleSelectAnswer("T")}
                    className="group flex items-center justify-between min-h-[64px] py-3 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-all active:scale-[0.98] text-left"
                  >
                    <span className="text-sm font-semibold">TAK</span>
                    <span className="w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent inline-flex items-center justify-center font-mono font-bold text-xs select-none">
                      T
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectAnswer("N")}
                    className="group flex items-center justify-between min-h-[64px] py-3 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-all active:scale-[0.98] text-left"
                  >
                    <span className="text-sm font-semibold">NIE</span>
                    <span className="w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent inline-flex items-center justify-center font-mono font-bold text-xs select-none">
                      N
                    </span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => handleSelectAnswer("A")}
                    className="group flex items-center justify-between min-h-[64px] py-3 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-all active:scale-[0.98] text-left"
                  >
                    <span className="text-sm font-medium leading-snug flex-1 pr-2">
                      {currentQ.a_pl}
                    </span>
                    <span className="w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent inline-flex items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                      A
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectAnswer("B")}
                    className="group flex items-center justify-between min-h-[64px] py-3 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-all active:scale-[0.98] text-left"
                  >
                    <span className="text-sm font-medium leading-snug flex-1 pr-2">
                      {currentQ.b_pl}
                    </span>
                    <span className="w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent inline-flex items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                      B
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectAnswer("C")}
                    className="group flex items-center justify-between min-h-[64px] py-3 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-all active:scale-[0.98] text-left"
                  >
                    <span className="text-sm font-medium leading-snug flex-1 pr-2">
                      {currentQ.c_pl}
                    </span>
                    <span className="w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent inline-flex items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                      C
                    </span>
                  </button>
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="py-8 text-center text-xs font-mono text-muted-foreground select-none">
            Brak pytań do sprawdzianu.
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
