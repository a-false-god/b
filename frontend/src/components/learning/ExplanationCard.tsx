import React, { useState, useEffect } from "react"
import { Scale } from "lucide-react"

interface ExplanationCardProps {
  questionId: number
  isCorrect?: boolean | null
  explanation?: string | null
  legalBasis?: string | null
  pending?: boolean
}

function renderInlineMarkdown(text: string): React.ReactNode[] {
  // Matches **bold**, *italic*, `code`
  const tokens = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return tokens.map((tok, idx) => {
    if (tok.startsWith("**") && tok.endsWith("**") && tok.length >= 4) {
      return (
        <strong key={idx} className="font-semibold text-foreground">
          {tok.slice(2, -2)}
        </strong>
      )
    }
    if (tok.startsWith("*") && tok.endsWith("*") && tok.length >= 2) {
      return (
        <em key={idx} className="italic text-foreground/90">
          {tok.slice(1, -1)}
        </em>
      )
    }
    if (tok.startsWith("`") && tok.endsWith("`") && tok.length >= 2) {
      return (
        <code
          key={idx}
          className="px-1 py-0.5 rounded bg-secondary text-foreground font-mono text-[0.9em]"
        >
          {tok.slice(1, -1)}
        </code>
      )
    }
    return tok
  })
}

function FormattedMarkdown({ content, className }: { content: string; className?: string }) {
  if (!content) return null
  const paragraphs = content.split(/\n\n+/)
  return (
    <div className={className || "space-y-2"}>
      {paragraphs.map((p, i) => {
        const lines = p.split(/\n/)
        return (
          <p key={i} className="leading-relaxed">
            {lines.map((line, lineIdx) => (
              <React.Fragment key={lineIdx}>
                {lineIdx > 0 && <br />}
                {renderInlineMarkdown(line)}
              </React.Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}

export function ExplanationCard({
  questionId,
  isCorrect,
  explanation: initialExplanation,
  legalBasis: initialLegalBasis,
  pending: initialPending,
}: ExplanationCardProps) {
  const [explanation, setExplanation] = useState(initialExplanation)
  const [legalBasis, setLegalBasis] = useState(initialLegalBasis)
  const [isPending, setIsPending] = useState(initialPending && !initialExplanation)

  useEffect(() => {
    setExplanation(initialExplanation)
    setLegalBasis(initialLegalBasis)
    setIsPending(Boolean(initialPending && !initialExplanation))
  }, [initialExplanation, initialLegalBasis, initialPending, questionId])

  useEffect(() => {
    if (!isPending) return

    let cancelled = false
    let attempts = 0
    const maxAttempts = 6

    const poll = async () => {
      while (!cancelled && attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 600))
        if (cancelled) break

        try {
          const res = await fetch(`/api/questions/${questionId}/explanation`)
          if (res.ok) {
            const data = await res.json()
            if (!data.pending && data.explanation) {
              setExplanation(data.explanation)
              setLegalBasis(data.legal_basis)
              setIsPending(false)
              break
            }
          }
        } catch {
          // ignore
        }
        attempts++
      }
      if (attempts >= maxAttempts && !cancelled) {
        setIsPending(false)
      }
    }

    poll()

    return () => {
      cancelled = true
    }
  }, [isPending, questionId])

  if (!explanation && !isPending) {
    return null
  }

  return (
    <div className="rounded-[12px] border border-border bg-secondary/40 p-3.5 sm:p-4 space-y-2.5 animate-slide-down">
      {/* Title with Verbal Verdict: "Dobrze." / "Nie tym razem." */}
      <div className="flex items-center justify-between text-xs font-mono font-semibold tracking-wide select-none">
        <div className="flex items-center gap-2">
          {isCorrect === true ? (
            <span className="text-success font-bold font-sans text-sm sm:text-base">
              Dobrze.
            </span>
          ) : isCorrect === false ? (
            <span className="text-destructive font-bold font-sans text-sm sm:text-base">
              Nie tym razem.
            </span>
          ) : (
            <span className="font-semibold font-sans text-foreground text-sm">
              Wyjaśnienie
            </span>
          )}
        </div>
        <span className="text-[10px] text-muted-foreground uppercase font-mono px-1.5 py-0.5 rounded-[6px] border border-border bg-background/50">
          Klawisz E
        </span>
      </div>

      {isPending ? (
        /* Reserved static skeleton per spec §3.3: 2-3 static lines, NO shimmer */
        <div className="space-y-2 py-1 select-none" aria-busy="true" aria-label="Wczytywanie objaśnienia">
          <div className="h-3.5 w-full bg-secondary/80 rounded" />
          <div className="h-3.5 w-11/12 bg-secondary/80 rounded" />
          <div className="h-3.5 w-3/4 bg-secondary/70 rounded" />
        </div>
      ) : (
        <>
          <FormattedMarkdown
            content={explanation || ""}
            className="text-type-body text-foreground/90 font-normal space-y-1.5"
          />

          {legalBasis && (
            <div className="pt-2 border-t border-border">
              <div className="flex items-center gap-1.5 text-[10px] font-mono font-semibold text-muted-foreground uppercase tracking-widest mb-1 select-none">
                <Scale className="w-3 h-3 text-muted-foreground" />
                <span>Podstawa Prawna</span>
              </div>
              <div className="text-type-data font-mono text-muted-foreground bg-background/80 p-2 rounded-[8px] border border-border leading-normal">
                <FormattedMarkdown content={legalBasis} className="space-y-1" />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
