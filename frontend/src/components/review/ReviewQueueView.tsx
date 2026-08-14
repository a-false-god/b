import { useState, useEffect, useCallback } from "react"
import { ReviewItem } from "@/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MediaViewer } from "@/components/media/MediaViewer"
import { useHotkeys } from "@/hooks/useHotkeys"
import { CheckCircle, ShieldCheck, Loader2 } from "lucide-react"

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
        setQueue(data)
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
    <div className="space-y-4 animate-fade-in-up pb-8">
      <div className="p-4 sm:p-5 rounded-[12px] border border-border bg-card">
        <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-accent" />
          <span>Kolejka Weryfikacji Taksonomii</span>
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5 font-mono select-none">
          Klasyfikacje LLM o pewności &lt; 0.8 lub z materiałem multimedialnym
        </p>
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
        <Card className="rounded-[12px] border border-border bg-card">
          <CardContent className="p-5 sm:p-6 space-y-4">
            {/* Metadata Pills */}
            <div className="flex flex-wrap items-center gap-1.5 font-mono text-[10px] select-none">
              <Badge variant="secondary" className="rounded-[4px]">Kat. B</Badge>
              <Badge variant="outline" className="rounded-[4px]">ID {currentItem.id}</Badge>
              <Badge variant="outline" className="rounded-[4px]">{currentItem.type}</Badge>
              <Badge variant="outline" className="rounded-[4px]">{currentItem.scope}</Badge>
              <span className="ml-auto text-muted-foreground">
                Pozostało: <strong className="text-foreground">{queue.length}</strong>
              </span>
            </div>

            {/* Media viewer if item has media */}
            {currentItem.media && (
              <MediaViewer
                media={currentItem.media}
                mediaKind={currentItem.media_kind}
                className="max-h-[220px]"
              />
            )}

            {/* Question Text */}
            <h2 className="text-base sm:text-lg font-medium text-foreground leading-snug">
              {currentItem.q_pl}
            </h2>

            {/* Suggestions Box */}
            <div className="p-4 rounded-[10px] border border-border bg-secondary/30 space-y-3">
              <div className="space-y-2.5 text-xs">
                <div>
                  <div className="flex items-center justify-between text-muted-foreground text-[10px] font-mono mb-1 select-none">
                    <span>Sugerowana Oś A (Poznawcza):</span>
                    <span>Pewność: <strong className="text-foreground font-mono">{((currentItem.conf_a || 0) * 100).toFixed(0)}%</strong></span>
                  </div>
                  <div className="flex items-center justify-between font-semibold text-foreground bg-card p-2.5 rounded-[8px] border border-border font-mono">
                    <span className="capitalize">{currentItem.sugg_a || "pamiec"}</span>
                    <div className="h-1.5 w-20 rounded-full bg-secondary overflow-hidden">
                      <div
                        className="h-full bg-accent"
                        style={{ width: `${(currentItem.conf_a || 0.6) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-muted-foreground text-[10px] font-mono mb-1 select-none">
                    <span>Sugerowana Oś B (Domena):</span>
                    <span>Pewność: <strong className="text-foreground font-mono">{((currentItem.conf_b || 0) * 100).toFixed(0)}%</strong></span>
                  </div>
                  <div className="flex items-center justify-between font-semibold text-foreground bg-card p-2.5 rounded-[8px] border border-border font-mono">
                    <span>{currentItem.sugg_b || "znaki_i_sygnaly"}</span>
                    <div className="h-1.5 w-20 rounded-full bg-secondary overflow-hidden">
                      <div
                        className="h-full bg-accent"
                        style={{ width: `${(currentItem.conf_b || 0.6) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons: Primary B/W Inverted button, Ghost skip */}
              <div className="pt-2 flex items-center gap-2">
                <Button
                  onClick={() => handleAction(1)}
                  disabled={submitting}
                  className="flex-1 bg-primary text-primary-foreground hover:opacity-90 font-semibold gap-2 h-10 text-xs font-mono rounded-[8px]"
                >
                  <kbd className="px-1.5 py-0.5 rounded-[4px] bg-background/20 text-[10px] font-mono">1</kbd>
                  <span>Akceptuj Sugestię</span>
                </Button>

                <Button
                  variant="ghost"
                  onClick={() => setQueue((prev) => prev.slice(1))}
                  className="text-xs text-muted-foreground hover:text-foreground h-10 px-3 font-mono rounded-[8px]"
                >
                  Pomiń
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
