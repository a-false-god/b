import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const plNumberFormatter = new Intl.NumberFormat("pl-PL")

export function formatCount(n: number | string | undefined | null): string {
  if (n === undefined || n === null) return "0"
  const num = typeof n === "string" ? parseInt(n, 10) : n
  if (isNaN(num)) return String(n)
  return plNumberFormatter.format(num)
}
