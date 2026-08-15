import * as React from "react"
import { cn } from "@/lib/utils"

interface ProgressHairlineProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  label?: string
}

export const ProgressHairline = React.forwardRef<HTMLDivElement, ProgressHairlineProps>(
  ({ value, max = 100, label, className, ...props }, ref) => {
    const percentage = Math.min(100, Math.max(0, max > 0 ? (value / max) * 100 : 0))
    const accessibleLabel = label || `Postęp: ${value} z ${max}`

    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={accessibleLabel}
        className={cn(
          "h-[2px] w-full bg-secondary/80 rounded-full overflow-hidden relative",
          className
        )}
        {...props}
      >
        <div
          className="h-full bg-accent rounded-full transition-all duration-base ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
    )
  }
)
ProgressHairline.displayName = "ProgressHairline"
