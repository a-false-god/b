import { useState, useEffect, useCallback } from "react"
import { ReviewItem } from "@/types"
import { Card, CardContent } from "@/components/ui/card"
import { MediaViewer } from "@/components/media/MediaViewer"
import { useHotkeys } from "@/hooks/useHotkeys"
import { CheckCircle, Loader2 } from "lucide-react"

export function ReviewQueueView() {
  const [queue, setQueue] = useState<ReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const loadQueue = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/classification/review", { credentials: "include" })
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data)) {
          setQueue(data)
        } else if (data && Array.isArray(data.items)) {
          // Normalize mock or wrapper response
          setQueue(
            data.items.map((item: any) => ({
              id: item.question_id || item.id,
              q_pl: item.q_pl,
              type: item.type || (item.q_pl?.includes("Czy") ? "TN" : "ABC"),
              scope: item.scope || "PODSTAWOWY",
              media: item.media || (item.has_media ? `${item.question_id || item.id}.mp4` : null),
              media_kind: item.media_kind || (item.has_media ? "video" : null),
              sugg_a: item.axis_a || item.sugg_a || "analiza",
              conf_a: item.confidence ?? item.conf_a ?? 0.6,
              sugg_b: item.axis_b || item.sugg_b || "pierwszenstwo",
              conf_b: item.confidence ?? item.conf_b ?? 0.6,
            }))
          )
        }
      }
    } catch {
      console.error("Failed to load review queue")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadQueue()
  }, [loadQueue])

  const currentItem = queue[0]

  const handleAction = async (actionNumber: number) => {
    if (!currentItem || submitting) return

    if (actionNumber === 3) {
      // Skip
      setQueue((prev) => prev.slice(1))
      return
    }

    setSubmitting(true)
    try {
      const axisA = currentItem.sugg_a || "pamiec"
      const axisB = currentItem.sugg_b || "znaki_i_sygnaly"

      await fetch(`/api/classification/${currentItem.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          axis_a: axisA,
          axis_b: axisB,
          axis_c: ["brak_pulapki"],
          action: actionNumber === 1 ? "accept" : "override",
        }),
      })

      // Pop from local queue
      setQueue((prev) => prev.slice(1))
    } catch (err) {
      console.error("Failed to submit classification review", err)
    } finally {
      setSubmitting(false)
    }
  }

  useHotkeys({
    onReviewAction: (num) => handleAction(num),
  })

  if (loading) {
    return (
      <div className="w-full min-h-[360px] rounded-[12px] border border-border bg-card flex flex-col items-center justify-center text-muted-foreground gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-accent" />
        <span className="text-xs font-mono">Wczytywanie kolejki weryfikacji...</span>
      </div>
    )
  }

  return (
    <div className="space-y-2.5 sm:space-y-3.5 animate-fade-in-up pb-6 sm:pb-8">
      {/* 1. Header with title, subtitle, and "zostało N" counter */}
      <div className="flex items-center justify-between gap-3 pt-0.5 pb-0.5">
        <div className="space-y-0.5 min-w-0">
          <h1 className="text-lg sm:text-2xl font-bold tracking-tight text-foreground truncate">
            Kolejka weryfikacji
          </h1>
          <p className="text-[11px] sm:text-xs text-muted-foreground font-sans select-none leading-snug">
            Niska pewność klasyfikacji — zatwierdź lub popraw osie.
          </p>
        </div>
        {queue.length > 0 && (
          <div className="text-xs font-mono text-muted-foreground select-none shrink-0 bg-secondary/60 px-2 py-1 rounded-md border border-border/50">
            zostało <strong className="text-foreground tabular-nums font-bold">{queue.length}</strong>
          </div>
        )}
      </div>

      {!currentItem ? (
        <Card className="rounded-[12px] border border-border bg-card text-center p-8 sm:p-12">
          <CardContent className="space-y-2">
            <CheckCircle className="w-8 h-8 text-foreground/80 mx-auto" />
            <h2 className="text-base font-bold text-foreground">Kolejka jest pusta</h2>
            <p className="text-xs text-muted-foreground font-mono">
              Wszystkie pytania zostały zweryfikowane lub posiadają wysoką pewność.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card className="rounded-[14px] border border-border bg-card overflow-hidden">
          <CardContent className="p-3.5 sm:p-5 space-y-2.5 sm:space-y-3.5">
            {/* 1. Full-width Media Container at top */}
            <div className="-mx-3.5 -mt-3.5 sm:mx-0 sm:mt-0 mb-3 sm:mb-0">
              <MediaViewer
                media={currentItem.media}
                mediaKind={currentItem.media_kind}
              />
            </div>

            {/* Meta top in faint mono: "ID 610 · T/N · KAT B" */}
            <div className="text-[10px] sm:text-[11px] font-mono text-faint tracking-wider uppercase select-none">
              ID {currentItem.id} · {currentItem.type === "TN" ? "T/N" : currentItem.type || "ABC"} · KAT B
            </div>

            {/* Question Text */}
            <h2 className="text-[14.5px] sm:text-[17px] font-bold text-foreground leading-snug">
              {currentItem.q_pl}
            </h2>

            {/* Suggestions with hairline confidence tracks */}
            <div className="space-y-2 pt-0.5">
              {/* Oś A */}
              <div className="space-y-1 select-none">
                <div className="flex items-baseline justify-between text-[11px] sm:text-xs">
                  <span className="text-muted-foreground font-sans">Oś A · poznawcza</span>
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-foreground font-sans">
                      {currentItem.sugg_a || "analiza"}
                    </span>
                    <span className="font-mono text-[10px] sm:text-[11px] text-muted-foreground tabular-nums">
                      {((currentItem.conf_a ?? 0.6) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="h-[2px] w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all"
                    style={{ width: `${(currentItem.conf_a ?? 0.6) * 100}%` }}
                  />
                </div>
              </div>

              {/* Oś B */}
              <div className="space-y-1 select-none">
                <div className="flex items-baseline justify-between text-[11px] sm:text-xs">
                  <span className="text-muted-foreground font-sans">Oś B · domena</span>
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-foreground font-sans">
                      {currentItem.sugg_b || "pierwszeństwo"}
                    </span>
                    <span className="font-mono text-[10px] sm:text-[11px] text-muted-foreground tabular-nums">
                      {((currentItem.conf_b ?? 0.6) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="h-[2px] w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all"
                    style={{ width: `${(currentItem.conf_b ?? 0.6) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Action Buttons: Touch-first large targets */}
            <div className="pt-1.5 grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleAction(1)}
                disabled={submitting}
                className="flex items-center justify-center gap-1.5 h-11 sm:h-10 px-2 rounded-[10px] bg-primary text-primary-foreground hover:opacity-90 active:scale-[0.98] transition-all font-semibold text-xs sm:text-sm select-none disabled:opacity-50"
              >
                <kbd className="hidden sm:inline-flex items-center justify-center w-4 h-4 rounded-[4px] bg-primary-foreground/20 text-primary-foreground font-mono text-[10px] font-bold">
                  1
                </kbd>
                <span>Akceptuj</span>
              </button>

              <button
                type="button"
                onClick={() => handleAction(2)}
                disabled={submitting}
                className="flex items-center justify-center gap-1.5 h-11 sm:h-10 px-2 rounded-[10px] border border-border bg-secondary hover:bg-secondary/80 active:scale-[0.98] text-foreground transition-all font-medium text-xs sm:text-sm select-none disabled:opacity-50"
              >
                <kbd className="hidden sm:inline-flex items-center justify-center w-4 h-4 rounded-[4px] bg-background border border-border text-muted-foreground font-mono text-[10px] font-bold">
                  2
                </kbd>
                <span>Popraw</span>
              </button>

              <button
                type="button"
                onClick={() => handleAction(3)}
                disabled={submitting}
                className="flex items-center justify-center gap-1.5 h-11 sm:h-10 px-2 rounded-[10px] border border-border bg-secondary hover:bg-secondary/80 active:scale-[0.98] text-foreground transition-all font-medium text-xs sm:text-sm select-none disabled:opacity-50"
              >
                <kbd className="hidden sm:inline-flex items-center justify-center w-4 h-4 rounded-[4px] bg-background border border-border text-muted-foreground font-mono text-[10px] font-bold">
                  3
                </kbd>
                <span>Pomiń</span>
              </button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
