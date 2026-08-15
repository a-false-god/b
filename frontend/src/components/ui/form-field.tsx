import * as React from "react"
import { cn } from "@/lib/utils"
import { AlertCircle } from "lucide-react"

interface FormFieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string
  error?: string | null
  required?: boolean
  htmlFor?: string
}

export const FormField = React.forwardRef<HTMLDivElement, FormFieldProps>(
  ({ label, error, required, htmlFor, className, children, ...props }, ref) => {
    const errorId = htmlFor ? `${htmlFor}-error` : undefined

    return (
      <div ref={ref} className={cn("space-y-1.5", className)} {...props}>
        <div className="flex items-center justify-between">
          <label
            htmlFor={htmlFor}
            className="text-type-ui font-medium text-foreground select-none block"
          >
            {label}
            {required && <span className="text-destructive ml-0.5">*</span>}
          </label>
        </div>

        <div>{children}</div>

        {/* Accessible inline error — with icon, never relying on color alone */}
        {error && (
          <div
            id={errorId}
            role="alert"
            className="flex items-center gap-1.5 text-xs text-destructive font-medium pt-0.5 animate-slide-down"
          >
            <AlertCircle className="w-3.5 h-3.5 shrink-0 text-destructive" />
            <span>{error}</span>
          </div>
        )}
      </div>
    )
  }
)
FormField.displayName = "FormField"
