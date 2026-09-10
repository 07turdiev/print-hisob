import { computed } from 'vue'
import { useTheme } from '../composables/useTheme'

/**
 * Diagrammalar uchun umumiy rang to'plami — dizayn tizimidagi rasmiy ko'k rangdan
 * boshlanadi va undan keyin ajralib turadigan yordamchi ranglar keladi.
 */
export const CHART_PALETTE = [
  '#0f5ba8',
  '#3d9be9',
  '#16897b',
  '#d99310',
  '#6a9b3f',
  '#c8442f',
  '#7b5ea7',
  '#4a6b8a',
]

interface DesignTokens {
  text: string
  textMuted: string
  border: string
  surface: string
  surface2: string
  accent: string
}

function readTokens(): DesignTokens {
  const styles = getComputedStyle(document.documentElement)
  const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback
  return {
    text: read('--color-text', '#1b2c3d'),
    textMuted: read('--color-text-muted', '#6a7c8d'),
    border: read('--color-border', '#d8e0e9'),
    surface: read('--color-surface', '#ffffff'),
    surface2: read('--color-surface-2', '#f5f7fa'),
    accent: read('--color-accent', '#0f5ba8'),
  }
}

/** `#rrggbb` rangni shaffoflik bilan `rgba(...)` ga o'giradi (gradient to'ldirishlar uchun). */
export function withAlpha(hex: string, alpha: number): string {
  const clean = hex.replace('#', '')
  if (clean.length !== 6) return hex
  const r = parseInt(clean.slice(0, 2), 16)
  const g = parseInt(clean.slice(2, 4), 16)
  const b = parseInt(clean.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/**
 * Barcha diagrammalar uchun yagona ECharts uslubi — qiymatlar jonli CSS
 * o'zgaruvchilaridan o'qiladi, shuning uchun mavzu almashganda diagramma ham o'zgaradi.
 */
export function useChartTheme() {
  const { theme } = useTheme()

  return computed(() => {
    // `theme.value` — qayta hisoblashni majburlaydigan reaktiv bog'liqlik; ranglarning
    // o'zi esa endigina qo'llangan CSS o'zgaruvchilaridan olinadi.
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
        extraCssText: 'box-shadow: var(--shadow-pop); border-radius: 4px; padding: 8px 12px;',
      },
    }
  })
}
