/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
          soft: "hsl(var(--destructive-soft))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
          soft: "hsl(var(--success-soft))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
          soft: "hsl(var(--warning-soft))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        faint: "hsl(var(--faint))",
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
          soft: "hsl(var(--accent-soft))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      fontSize: {
        "type-question": ["1.4375rem", { lineHeight: "1.3", letterSpacing: "-0.015em", fontWeight: "700" }],
        "type-title": ["1.125rem", { lineHeight: "1.3", letterSpacing: "-0.015em", fontWeight: "600" }],
        "type-body": ["0.875rem", { lineHeight: "1.45", fontWeight: "400" }],
        "type-ui": ["0.8125rem", { lineHeight: "1.25", fontWeight: "500" }],
        "type-data": ["0.75rem", { lineHeight: "1.25", fontWeight: "600" }],
        "type-caption": ["0.6875rem", { lineHeight: "1.2", fontWeight: "400" }],
      },
      transitionDuration: {
        instant: "80ms",
        fast: "120ms",
        base: "160ms",
        slow: "200ms",
      },
      borderRadius: {
        xl: "18px",
        lg: "12px",
        md: "8px",
        sm: "6px",
      },
      fontFamily: {
        sans: ["'Inter'", "-apple-system", "BlinkMacSystemFont", "'Segoe UI'", "Roboto", "sans-serif"],
        display: ["'Inter'", "-apple-system", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "'Liberation Mono'", "'Courier New'", "monospace"],
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(2px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          "0%": { opacity: "0", transform: "translateY(-2px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 120ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "slide-down": "slide-down 160ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
    },
  },
  plugins: [],
}

