import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { FormField } from "@/components/ui/form-field"
import { User } from "@/types"
import { AlertCircle } from "lucide-react"

interface AuthModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (user: User) => void
  initialMessage?: string
}

export function AuthModal({
  open,
  onOpenChange,
  onSuccess,
  initialMessage,
}: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [login, setLogin] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(initialMessage || null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!login.trim() || !password) {
      setError("Wprowadź login oraz hasło.")
      return
    }

    setError(null)
    setLoading(true)

    const endpoint = mode === "login" ? "/auth/login" : "/auth/register"

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ login: login.trim(), password }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || "Wystąpił błąd autoryzacji.")
        setLoading(false)
        return
      }

      const userData: User = await res.json()
      localStorage.setItem("prawko_user", JSON.stringify(userData))
      onSuccess(userData)
      onOpenChange(false)
      setLogin("")
      setPassword("")
    } catch {
      setError("Błąd połączenia z serwerem.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent hideCloseButton className="sm:max-w-[400px] rounded-[12px] border border-border bg-card modal-shadow p-6 sm:p-7">
        <DialogHeader className="space-y-1 text-center sm:text-center">
          {/* Wordmark: Mono uppercase spaced */}
          <DialogTitle className="font-mono text-xs sm:text-sm font-bold tracking-[0.25em] text-foreground uppercase select-none text-center">
            PRAWKO<span className="text-muted-foreground font-normal">//</span>B
          </DialogTitle>
          {/* Subtitle */}
          <DialogDescription className="text-xs text-muted-foreground text-center select-none">
            Nauka na kat. B — z analizą błędów
          </DialogDescription>
        </DialogHeader>

        {/* Segmented Control */}
        <div className="grid grid-cols-2 p-1 bg-secondary/80 rounded-[8px] border border-border/50 mt-2">
          <button
            type="button"
            onClick={() => {
              setMode("login")
              setError(null)
            }}
            className={`h-8 rounded-[6px] text-xs font-medium transition-all select-none ${
              mode === "login"
                ? "bg-card text-foreground font-semibold shadow-sm border border-border/40"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Logowanie
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("register")
              setError(null)
            }}
            className={`h-8 rounded-[6px] text-xs font-medium transition-all select-none ${
              mode === "register"
                ? "bg-card text-foreground font-semibold shadow-sm border border-border/40"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Rejestracja
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-[8px] bg-destructive-soft border border-destructive/30 text-destructive text-xs font-medium animate-slide-down">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 pt-1">
          <FormField label="Login" htmlFor="auth-login">
            <Input
              id="auth-login"
              type="text"
              placeholder="np. mike"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              disabled={loading}
              className="rounded-[8px] h-10 text-xs sm:text-sm font-sans bg-card border-input"
              autoFocus
            />
          </FormField>

          <FormField label="Hasło" htmlFor="auth-password">
            <Input
              id="auth-password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className="rounded-[8px] h-10 text-xs sm:text-sm font-sans bg-card border-input"
            />
          </FormField>

          <div className="pt-2 space-y-3">
            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-primary-foreground hover:opacity-90 font-semibold rounded-[8px] h-10 text-xs sm:text-sm font-sans transition-opacity select-none"
            >
              {loading
                ? "Przetwarzanie..."
                : mode === "login"
                ? "Zaloguj się"
                : "Utwórz konto"}
            </Button>

            {/* Quiet Footer Note */}
            <div className="text-[10px] font-mono tracking-[0.2em] text-faint uppercase text-center pt-1 select-none">
              localhost · konto lokalne
            </div>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
