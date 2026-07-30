import { computed } from 'vue'
import { useTheme } from '../composables/useTheme'

/** Shared categorical palette for every chart in the app (indigo/violet led). */
export const CHART_PALETTE = [
  '#6366f1',
  '#8b5cf6',
  '#06b6d4',
  '#f59e0b',
  '#10b981',
  '#f43f5e',
  '#0ea5e9',
  '#a855f7',
]

interface DesignTokens {
  text: string
  textMuted: string
  border: string
  surface: string
  surface2: string
}

function readTokens(): DesignTokens {
  const styles = getComputedStyle(document.documentElement)
  const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback
  return {
    text: read('--color-text', '#171a23'),
    textMuted: read('--color-text-muted', '#5b6472'),
    border: read('--color-border', '#e6e8f0'),
    surface: read('--color-surface', '#ffffff'),
    surface2: read('--color-surface-2', '#f2f3f9'),
  }
}

/**
 * Shared ECharts styling derived from the live CSS design tokens, so every chart component
 * (TimeseriesChart, NamedBarChart, ...) looks identical and reacts when the theme toggles.
 * Colors are read straight from the DOM's computed CSS variables rather than duplicated here.
 */
export function useChartTheme() {
  const { theme } = useTheme()

  return computed(() => {
    // `theme.value` is the reactive dependency that forces recomputation on toggle; the
    // actual color values always come from the CSS variables that were just applied.
    void theme.value
    const tokens = readTokens()

    return {
      palette: CHART_PALETTE,
      colors: tokens,
      textStyle: { fontFamily: 'inherit', color: tokens.text },
      axisLine: { lineStyle: { color: tokens.border } },
      axisLabel: { color: tokens.textMuted },
      splitLine: { lineStyle: { color: tokens.border, type: 'dashed' as const } },
      tooltip: {
        backgroundColor: tokens.surface,
        borderColor: tokens.border,
        borderWidth: 1,
        textStyle: { color: tokens.text },
        extraCssText: 'box-shadow: var(--shadow-pop); border-radius: 10px; padding: 8px 12px;',
      },
    }
  })
}
