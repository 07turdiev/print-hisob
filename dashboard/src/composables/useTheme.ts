import { ref, watchEffect } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'printerhisob.theme'

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const stored = localStorage.getItem(STORAGE_KEY)
const theme = ref<Theme>(stored === 'light' || stored === 'dark' ? stored : systemPrefersDark() ? 'dark' : 'light')

watchEffect(() => {
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem(STORAGE_KEY, theme.value)
})

/** App-wide light/dark theme, persisted to localStorage and shared across every consumer. */
export function useTheme() {
  function toggle() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  return { theme, toggle }
}
