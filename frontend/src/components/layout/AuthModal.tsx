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
import { User } from "@/types"
import { LogIn, UserPlus, AlertCircle } from "lucide-react"

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
      <DialogContent className="sm:max-w-[400px] rounded-[12px] border border-border bg-card modal-shadow p-5 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold flex items-center gap-2 text-foreground">
            {mode === "login" ? <LogIn className="w-4 h-4 text-accent" /> : <UserPlus className="w-4 h-4 text-accent" />}
            {mode === "login" ? "Logowanie" : "Rejestracja konta"}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            {mode === "login"
              ? "Wprowadź dane, aby rejestrować odpowiedzi i budować model Rascha."
              : "Utwórz konto w systemie — wszystkie sesje i postęp zostaną zapisane."}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-[8px] bg-destructive/10 border border-destructive/20 text-destructive text-xs font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          <div className="space-y-1">
            <label className="text-[11px] font-mono font-semibold uppercase tracking-wider text-muted-foreground block select-none">
              Login
            </label>
            <Input
              type="text"
              placeholder="np. kierowca_123"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              disabled={loading}
              className="rounded-[8px] h-9 text-xs font-mono"
              autoFocus
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-mono font-semibold uppercase tracking-wider text-muted-foreground block select-none">
              Hasło
            </label>
            <Input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className="rounded-[8px] h-9 text-xs font-mono"
            />
          </div>

          <div className="flex flex-col gap-2 pt-2">
            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-primary-foreground hover:opacity-90 font-semibold rounded-[8px] h-9 text-xs font-mono"
            >
              {loading
                ? "Przetwarzanie..."
                : mode === "login"
                ? "Zaloguj się"
                : "Zarejestruj"}
            </Button>

            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login")
                setError(null)
              }}
              className="text-xs text-muted-foreground hover:text-foreground text-center pt-1 transition-colors font-mono"
            >
              {mode === "login"
                ? "Nie masz jeszcze konta? Zarejestruj się"
                : "Masz już konto? Zaloguj się"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
