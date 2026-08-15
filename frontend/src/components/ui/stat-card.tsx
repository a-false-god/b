import * as React from "react"
import { cn } from "@/lib/utils"

export interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  className?: string
  color?: string
}

export function Sparkline({
  data,
  width = 160,
  height = 40,
  className,
  color = "hsl(var(--accent))",
}: SparklineProps) {
  if (!data || data.length === 0) return null

  const padX = 3
  const padY = 4

  let points: Array<{ x: number; y: number }> = []

  if (data.length >= 2) {
    const minVal = Math.min(...data)
    const maxVal = Math.max(...data)
    const range = maxVal - minVal || 1

    points = data.map((val, i) => {
      const x = padX + (i / (data.length - 1)) * (width - padX * 2)
      const normY = (val - minVal) / range
      const y = height - padY - normY * (height - padY * 2)
      return { x, y }
    })
  } else {
    points = [
      { x: padX, y: height / 2 },
      { x: width - padX, y: height / 2 },
    ]
  }

  const polylineStr = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")
  const areaPathStr = `M ${points[0].x.toFixed(1)},${height} L ${points
    .map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(" L ")} L ${points[points.length - 1].x.toFixed(1)},${height} Z`

  const lastPoint = points[points.length - 1]

  return (
    <div className={cn("relative overflow-hidden", className)}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="w-full h-full block"
      >
        <defs>
          <linearGradient id="stat-sparkline-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Immediate area render — no draw animations per motion budget */}
        <path d={areaPathStr} fill="url(#stat-sparkline-gradient)" />

        {/* Immediate polyline render */}
        <polyline
          points={polylineStr}
          fill="none"
          stroke={color}
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* 4px end dot per spec */}
        {lastPoint && (
          <circle
            cx={lastPoint.x}
            cy={lastPoint.y}
            r="2"
            fill={color}
            stroke="hsl(var(--card))"
            strokeWidth="1.2"
          />
        )}
      </svg>
    </div>
  )
}

interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: string | number
  unit?: string
  trend?: string
  sparklineData?: number[]
}

export function StatCard({
  title,
  value,
  unit,
  trend,
  sparklineData,
  className,
  children,
  ...props
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-[12px] border border-border bg-card p-3.5 space-y-2 select-none",
        className
      )}
      {...props}
    >
      <div className="text-type-caption text-muted-foreground font-medium">
        {title}
      </div>

      <div className="flex items-baseline gap-1.5 font-mono">
        <span className="text-xl sm:text-2xl font-bold text-foreground tabular-nums leading-none">
          {value}
        </span>
        {unit && (
          <span className="text-xs text-muted-foreground font-normal">
            {unit}
          </span>
        )}
      </div>

      {trend && (
        <div className="text-type-caption text-muted-foreground font-mono">
          {trend}
        </div>
      )}

      {sparklineData && sparklineData.length > 0 && (
        <Sparkline data={sparklineData} className="h-8 w-full mt-1" />
      )}

      {children}
    </div>
  )
}
