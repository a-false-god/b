import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { MediaViewer } from "@/components/media/MediaViewer"
import { ProgressHairline } from "@/components/ui/progress-hairline"
import { Question, ExamSubmissionResponse } from "@/types"
import { Clock, CheckCircle2, XCircle, Loader2, AlertTriangle } from "lucide-react"

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
  const [confirmExit, setConfirmExit] = useState(false)

  // Start exam
  useEffect(() => {
    if (!open) {
      setReport(null)
      setQuestions([])
      setAnswers([])
      setConfirmExit(false)
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
          setConfirmExit(false)
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
    if (!open || report || loading || questions.length === 0 || confirmExit) return

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
  }, [open, report, loading, questions.length, answers, confirmExit])

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

  const handleAbortExam = () => {
    setConfirmExit(false)
    onOpenChange(false)
  }

  const formatTimer = (sec: number) => {
    const mins = Math.floor(sec / 60)
    const s = sec % 60
    return `${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  }

  // D9: Urgent state at 02:00 (<= 120s) — one-time static style change, NO pulse animation
  const isUrgent = remainingSeconds <= 120

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        hideCloseButton
        className="fixed inset-0 w-screen h-[100dvh] max-w-none max-h-none rounded-none border-none bg-background/95 backdrop-blur-md flex flex-col p-4 sm:p-6 overflow-y-auto z-50 animate-fade-in-up"
      >
        <div className="w-full max-w-[540px] mx-auto flex-1 flex flex-col justify-between py-2">
          {/* Header Bar */}
          <DialogHeader className="pb-2">
            <div className="flex items-center justify-between gap-3">
              <DialogTitle className="text-sm sm:text-base font-bold font-mono text-foreground uppercase tracking-wider">
                Sprawdzian Gotowości
              </DialogTitle>

              <div className="flex items-center gap-2.5">
                {!report && questions.length > 0 && (
                  <div
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] font-mono text-xs tabular-nums border select-none transition-colors duration-fast ${
                      isUrgent
                        ? "bg-destructive-soft text-destructive border-destructive/40 font-bold"
                        : "bg-secondary/80 text-foreground border-border/80 font-semibold"
                    }`}
                  >
                    <Clock className="w-3.5 h-3.5" />
                    <span>{formatTimer(remainingSeconds)}</span>
                  </div>
                )}

                {/* Exit button with confirmation trigger */}
                {!report && (
                  <button
                    type="button"
                    onClick={() => setConfirmExit(true)}
                    className="px-2.5 py-1 rounded-[6px] border border-border bg-secondary/80 text-muted-foreground hover:text-foreground text-xs font-mono transition-colors"
                  >
                    Przerwij
                  </button>
                )}
              </div>
            </div>
          </DialogHeader>

          {/* Confirm Exit Modal / Interstitial */}
          {confirmExit ? (
            <div className="p-6 rounded-[12px] border border-border bg-card text-center space-y-4 my-auto animate-slide-down">
              <div className="w-10 h-10 rounded-full bg-destructive-soft border border-destructive/30 flex items-center justify-center mx-auto text-destructive">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-foreground">
                  Przerwać sprawdzian?
                </h3>
                <p className="text-xs text-muted-foreground font-mono">
                  Dotychczasowe odpowiedzi nie zostaną zapisane w wynikach.
                </p>
              </div>
              <div className="flex items-center justify-center gap-3 pt-2">
                <Button
                  variant="outline"
                  onClick={() => setConfirmExit(false)}
                  className="font-mono text-xs"
                >
                  Kontynuuj sprawdzian
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleAbortExam}
                  className="font-mono text-xs"
                >
                  Przerwij sprawdzian
                </Button>
              </div>
            </div>
          ) : loading ? (
            <div className="py-24 flex flex-col items-center justify-center text-muted-foreground gap-3 my-auto">
              <Loader2 className="w-5 h-5 animate-spin text-accent" />
              <span className="text-xs font-mono">Generowanie arkusza 32 pytań...</span>
            </div>
          ) : report ? (
            /* Final Report */
            <div className="py-6 text-center space-y-5 my-auto animate-slide-down">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full mx-auto bg-secondary border border-border">
                {report.passed ? (
                  <CheckCircle2 className="w-8 h-8 text-success" />
                ) : (
                  <XCircle className="w-8 h-8 text-destructive" />
                )}
              </div>

              <div>
                <h2 className="text-xl sm:text-2xl font-bold font-mono tracking-tight">
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
            <div className="py-24 flex flex-col items-center justify-center text-muted-foreground gap-3 my-auto">
              <Loader2 className="w-5 h-5 animate-spin text-accent" />
              <span className="text-xs font-mono">Podliczanie wyników egzaminu...</span>
            </div>
          ) : currentQ ? (
            /* Question Exam Card (NO semantic states during exam) */
            <div className="space-y-4 py-2 my-auto">
              {/* Progress hairline + counter */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground select-none">
                  <span className="uppercase tracking-wider">Arkusz egzaminacyjny</span>
                  <span className="tabular-nums font-semibold text-foreground">
                    {currentIndex + 1} / {questions.length}
                  </span>
                </div>
                <ProgressHairline
                  value={currentIndex + 1}
                  max={questions.length}
                  label={`Pytanie egzaminacyjne ${currentIndex + 1} z ${questions.length}`}
                />
              </div>

              {/* Scope / points chips: OUTLINE mono, not filled */}
              <div className="flex items-center gap-1.5 pt-0.5">
                <span className="px-2 py-0.5 rounded-[6px] border border-border/80 text-muted-foreground text-[10px] font-mono uppercase tracking-wider select-none">
                  {currentQ.scope}
                </span>
                <span className="px-2 py-0.5 rounded-[6px] border border-border/80 text-muted-foreground text-[10px] font-mono uppercase tracking-wider tabular-nums select-none">
                  {currentQ.points} PKT
                </span>
              </div>

              {/* Media Container (full-width on mobile) */}
              <div className="-mx-4 sm:mx-0">
                <MediaViewer
                  media={currentQ.media}
                  mediaKind={currentQ.media_kind}
                  className="rounded-none sm:rounded-[12px]"
                />
              </div>

              {/* Question Text */}
              <h3 className="text-base sm:text-lg font-bold leading-snug text-foreground">
                {currentQ.q_pl}
              </h3>

              {/* Answer Options — NO semantic correctness states during exam */}
              <div className="grid gap-2.5 pt-1">
                {currentQ.type === "TN" ? (
                  <div className="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={() => handleSelectAnswer("T")}
                      className="group flex items-center justify-center min-h-[54px] sm:min-h-[64px] py-3 px-3.5 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-colors active:scale-[0.98] text-center select-none"
                    >
                      <div className="flex items-center justify-center gap-2 w-full">
                        <span className="hidden [@media(pointer:fine)]:inline-flex w-[28px] h-[28px] rounded-[7px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                          T
                        </span>
                        <span className="font-bold text-base sm:text-lg tracking-wider text-foreground">
                          Tak
                        </span>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectAnswer("N")}
                      className="group flex items-center justify-center min-h-[54px] sm:min-h-[64px] py-3 px-3.5 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-colors active:scale-[0.98] text-center select-none"
                    >
                      <div className="flex items-center justify-center gap-2 w-full">
                        <span className="hidden [@media(pointer:fine)]:inline-flex w-[28px] h-[28px] rounded-[7px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                          N
                        </span>
                        <span className="font-bold text-base sm:text-lg tracking-wider text-foreground">
                          Nie
                        </span>
                      </div>
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => handleSelectAnswer("A")}
                      className="group flex items-center min-h-[64px] py-3.5 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-colors active:scale-[0.99] text-left select-none"
                    >
                      <div className="flex items-center gap-3.5 w-full">
                        <span className="hidden [@media(pointer:fine)]:inline-flex w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                          A
                        </span>
                        <span className="text-type-body font-normal leading-snug text-foreground flex-1">
                          {currentQ.a_pl}
                        </span>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectAnswer("B")}
                      className="group flex items-center min-h-[64px] py-3.5 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-colors active:scale-[0.99] text-left select-none"
                    >
                      <div className="flex items-center gap-3.5 w-full">
                        <span className="hidden [@media(pointer:fine)]:inline-flex w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                          B
                        </span>
                        <span className="text-type-body font-normal leading-snug text-foreground flex-1">
                          {currentQ.b_pl}
                        </span>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectAnswer("C")}
                      className="group flex items-center min-h-[64px] py-3.5 px-4 rounded-[12px] border-[1.5px] border-border bg-card text-foreground hover:border-accent transition-colors active:scale-[0.99] text-left select-none"
                    >
                      <div className="flex items-center gap-3.5 w-full">
                        <span className="hidden [@media(pointer:fine)]:inline-flex w-[30px] h-[30px] rounded-[8px] border border-border bg-secondary text-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:border-accent items-center justify-center font-mono font-bold text-xs shrink-0 select-none">
                          C
                        </span>
                        <span className="text-type-body font-normal leading-snug text-foreground flex-1">
                          {currentQ.c_pl}
                        </span>
                      </div>
                    </button>
                  </>
                )}
              </div>

              {/* Quiet footer note */}
              <div className="text-type-caption text-muted-foreground text-center select-none pt-2">
                Bez podpowiedzi — jak na egzaminie państwowym.
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-xs font-mono text-muted-foreground select-none my-auto">
              Brak pytań do sprawdzianu.
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
