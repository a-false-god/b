import { Component, ErrorInfo, ReactNode } from "react"
import { AlertCircle, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[Prawko B ErrorBoundary] Uncaught component error:", error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  public render() {
    if (this.state.hasError) {
      if (this.fallback) {
        return this.fallback
      }

      return (
        <div className="min-h-[50vh] flex flex-col items-center justify-center p-6 text-center">
          <div className="w-full max-w-md p-6 rounded-2xl border border-border/50 bg-card/80 backdrop-blur shadow-sm space-y-4">
            <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold tracking-tight text-foreground">
                Coś poszło nie tak
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Wystąpił nieoczekiwany błąd podczas wyświetlania widoku. Stan aplikacji został zachowany.
              </p>
            </div>
            {this.state.error && (
              <div className="p-2.5 rounded-lg bg-muted/50 border border-border/30 text-xs font-mono text-muted-foreground text-left overflow-x-auto max-h-24">
                {this.state.error.message}
              </div>
            )}
            <div className="pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={this.handleReset}
                className="gap-2 border-border/60 hover:bg-accent"
              >
                <RotateCcw className="w-4 h-4" />
                Odśwież aplikację
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }

  private get fallback() {
    return this.props.fallback
  }
}
