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
    <div className="space-y-3.5 animate-fade-in-up pb-8">
      {/* 1. Header with title, subtitle, and "zostało N" counter */}
      <div className="flex items-start justify-between gap-3 pt-1 pb-0.5">
        <div className="space-y-0.5">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Kolejka weryfikacji
          </h1>
          <p className="text-xs text-muted-foreground font-sans select-none">
            Niska pewność klasyfikacji — zatwierdź lub popraw osie.
          </p>
        </div>
        {queue.length > 0 && (
          <div className="text-xs font-mono text-muted-foreground select-none pt-1 shrink-0">
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
        <Card className="rounded-[12px] border border-border bg-card overflow-hidden">
          <CardContent className="p-4 sm:p-5 space-y-3.5">
            {/* Meta top in faint mono: "ID 610 · T/N · KAT B" */}
            <div className="text-[11px] font-mono text-faint tracking-wider uppercase select-none">
              ID {currentItem.id} · {currentItem.type === "TN" ? "T/N" : currentItem.type || "ABC"} · KAT B
            </div>

            {/* Media thumbnail */}
            {currentItem.media ? (
              <MediaViewer
                media={currentItem.media}
                mediaKind={currentItem.media_kind}
                className="max-h-[220px]"
              />
            ) : (
              <div className="w-full aspect-video rounded-[12px] border border-border bg-secondary/30 flex items-center justify-center text-muted-foreground select-none">
                <span className="text-xs font-mono text-faint">Brak materiału wizualnego</span>
              </div>
            )}

            {/* Question Text */}
            <h2 className="text-base sm:text-[17px] font-bold text-foreground leading-snug">
              {currentItem.q_pl}
            </h2>

            {/* Suggestions with hairline confidence tracks */}
            <div className="space-y-3 pt-1">
              {/* Oś A */}
              <div className="space-y-1.5 select-none">
                <div className="flex items-baseline justify-between text-xs">
                  <span className="text-muted-foreground font-sans">Oś A · poznawcza</span>
                  <div className="flex items-baseline gap-3">
                    <span className="font-bold text-foreground font-sans">
                      {currentItem.sugg_a || "analiza"}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                      {((currentItem.conf_a ?? 0.6) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="h-[2.5px] w-full rounded-full bg-secondary/80 overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all"
                    style={{ width: `${(currentItem.conf_a ?? 0.6) * 100}%` }}
                  />
                </div>
              </div>

              {/* Oś B */}
              <div className="space-y-1.5 select-none">
                <div className="flex items-baseline justify-between text-xs">
                  <span className="text-muted-foreground font-sans">Oś B · domena</span>
                  <div className="flex items-baseline gap-3">
                    <span className="font-bold text-foreground font-sans">
                      {currentItem.sugg_b || "pierwszeństwo"}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                      {((currentItem.conf_b ?? 0.6) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="h-[2.5px] w-full rounded-full bg-secondary/80 overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all"
                    style={{ width: `${(currentItem.conf_b ?? 0.6) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Action Buttons: Inverted B/W Accept, Secondary Popraw, Secondary Pomiń */}
            <div className="pt-2 grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleAction(1)}
                disabled={submitting}
                className="flex items-center justify-center gap-2 h-10 px-3 rounded-[8px] bg-primary text-primary-foreground hover:opacity-90 transition-opacity font-semibold text-xs select-none disabled:opacity-50"
              >
                <kbd className="inline-flex items-center justify-center w-4 h-4 rounded-[4px] bg-primary-foreground/20 text-primary-foreground font-mono text-[10px] font-bold">
                  1
                </kbd>
                <span>Akceptuj</span>
              </button>

              <button
                type="button"
                onClick={() => handleAction(2)}
                disabled={submitting}
                className="flex items-center justify-center gap-2 h-10 px-3 rounded-[8px] border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors font-medium text-xs select-none disabled:opacity-50"
              >
                <kbd className="inline-flex items-center justify-center w-4 h-4 rounded-[4px] bg-background border border-border text-muted-foreground font-mono text-[10px] font-bold">
                  2
                </kbd>
                <span>Popraw</span>
              </button>

              <button
                type="button"
                onClick={() => handleAction(3)}
                disabled={submitting}
                className="flex items-center justify-center gap-2 h-10 px-3 rounded-[8px] border border-border bg-secondary hover:bg-secondary/80 text-foreground transition-colors font-medium text-xs select-none disabled:opacity-50"
              >
                <kbd className="inline-flex items-center justify-center w-4 h-4 rounded-[4px] bg-background border border-border text-muted-foreground font-mono text-[10px] font-bold">
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
