<script setup lang="ts">
import { computed } from 'vue'
import type { StatsSummary } from '../api/types'
import StatTile from './StatTile.vue'

const props = defineProps<{ summary: StatsSummary | null }>()

const numberFormat = new Intl.NumberFormat('uz-UZ')

function fmt(value: number | undefined): string {
  return value === undefined ? '—' : numberFormat.format(value)
}

const successRate = computed(() => props.summary?.successRate ?? null)

const successPercent = computed(() =>
  successRate.value === null ? '—' : `${Math.round(successRate.value * 1000) / 10}%`,
)

/** Muvaffaqiyat darajasi past bo'lsa kartochka rangi ogohlantiruvchiga o'zgaradi. */
const successTone = computed(() => {
  if (successRate.value === null) return 'muted' as const
  if (successRate.value >= 0.98) return 'success' as const
  if (successRate.value >= 0.9) return 'accent' as const
  return 'danger' as const
})

const failedHint = computed(() => {
  const s = props.summary
  if (!s) return undefined
  const failed = Math.max(0, s.totalJobs - Math.round(s.totalJobs * s.successRate))
  return failed > 0 ? `${numberFormat.format(failed)} ta xatolik` : 'Xatoliksiz'
})
</script>

<template>
  <div class="grid-3">
    <StatTile label="Jami varaqlar" :value="fmt(summary?.totalPages)" icon="pages" hint="Sarflangan qog'oz" />
    <StatTile
      label="Jami buyurtmalar"
      :value="fmt(summary?.totalJobs)"
      icon="layers"
      hint="Chop etish hodisalari"
    />
    <StatTile
      label="Muvaffaqiyat darajasi"
      :value="successPercent"
      icon="check-circle"
      :tone="successTone"
      :hint="failedHint"
    />
    <StatTile label="Faol printerlar" :value="fmt(summary?.activePrinters)" icon="printers" hint="Davr ichida ishlagan" />
  </div>
</template>
