/**
 * Chart.js color constants derived from the Tailwind config design tokens.
 * Centralizes color definitions so Chart.js components don't use inline hex.
 *
 * These values MUST match the corresponding Tailwind config entries in tailwind.config.js.
 */

export const chartColors = {
  primary: {
    800: 'rgb(30, 64, 175)',      // primary-800
    500: 'rgb(59, 130, 246)',      // primary-500
    900: 'rgb(30, 58, 138)',       // primary-900
    bg: 'rgba(30, 64, 175, 0.1)',  // primary-800 at 10%
    bg20: 'rgba(30, 64, 175, 0.2)', // primary-800 at 20%
  },
  warning: {
    500: 'rgb(245, 158, 11)',      // warning-500
  },
  success: {
    600: 'rgb(5, 150, 105)',       // success/emerald-600
  },
  danger: {
    500: 'rgb(239, 68, 68)',       // danger-500 / red-500
    600: 'rgb(220, 38, 38)',       // danger-600 / red-600
  },
  purple: 'rgb(139, 92, 246)',     // violet-500
  emerald: 'rgb(16, 185, 129)',    // emerald-500
  amber: 'rgb(217, 119, 6)',       // amber-600
  pink: 'rgb(236, 72, 153)',       // pink-500
  violet: 'rgb(124, 58, 237)',     // violet-600
} as const

/** Engine-specific colors for chart datasets */
export const engineColors: Record<string, string> = {
  chatgpt: chartColors.emerald,
  claude: chartColors.purple,
  perplexity: chartColors.primary[500],
  gemini: chartColors.warning[500],
}

/** Competitor chart colors (border) */
export const competitorColors = [
  chartColors.danger[500],
  chartColors.warning[500],
  chartColors.emerald,
  chartColors.purple,
  chartColors.pink,
]

/** Competitor chart colors (background, 10% opacity) */
export const competitorBgColors = [
  'rgba(239, 68, 68, 0.1)',
  'rgba(245, 158, 11, 0.1)',
  'rgba(16, 185, 129, 0.1)',
  'rgba(139, 92, 246, 0.1)',
  'rgba(236, 72, 153, 0.1)',
]
