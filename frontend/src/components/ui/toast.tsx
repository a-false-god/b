import * as React from "react"
import { cn } from "@/lib/utils"
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react"

export type ToastType = "info" | "success" | "error"

export interface ToastItem {
  id: string
  title?: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastContextType {
  toasts: ToastItem[]
  showToast: (message: string, type?: ToastType, title?: string, duration?: number) => void
  dismissToast: (id: string) => void
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined)

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return context
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([])

  const dismissToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = React.useCallback(
    (message: string, type: ToastType = "info", title?: string, duration?: number) => {
      const id = "toast_" + Math.random().toString(36).substring(2, 9)
      const autoDismissTime = duration || (type === "error" ? 8000 : 4000)

      setToasts((prev) => {
        // Spec: Max 2 visible toasts
        const trimmed = prev.slice(-1)
        return [...trimmed, { id, message, type, title, duration: autoDismissTime }]
      })

      setTimeout(() => {
        dismissToast(id)
      }, autoDismissTime)
    },
    [dismissToast]
  )

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>
      {children}
      {/* Toast Region */}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-[calc(100%-2rem)] pointer-events-none"
      >
        {toasts.map((t) => {
          const isError = t.type === "error"
          const isSuccess = t.type === "success"

          return (
            <div
              key={t.id}
              role={isError ? "alert" : "status"}
              aria-atomic="true"
              className={cn(
                "pointer-events-auto p-3.5 rounded-[10px] border shadow-lg flex items-start gap-3 bg-card text-foreground transition-all duration-fast animate-slide-down",
                isError && "border-destructive/40 bg-destructive-soft",
                isSuccess && "border-success/40 bg-success-soft",
                !isError && !isSuccess && "border-border bg-card"
              )}
            >
              {isError ? (
                <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
              ) : isSuccess ? (
                <CheckCircle2 className="w-4 h-4 text-success shrink-0 mt-0.5" />
              ) : (
                <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
              )}

              <div className="flex-1 space-y-0.5">
                {t.title && (
                  <div className="text-xs font-semibold text-foreground">
                    {t.title}
                  </div>
                )}
                <div className="text-xs text-foreground/90 leading-snug">
                  {t.message}
                </div>
              </div>

              <button
                type="button"
                onClick={() => dismissToast(t.id)}
                className="text-muted-foreground hover:text-foreground p-0.5 rounded transition-colors"
                aria-label="Zamknij powiadomienie"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
