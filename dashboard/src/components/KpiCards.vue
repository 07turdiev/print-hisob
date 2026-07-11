<script setup lang="ts">
import { computed } from 'vue'
import type { StatsSummary } from '../api/types'

const props = defineProps<{ summary: StatsSummary | null }>()

const successPercent = computed(() => {
  if (!props.summary) return '-'
  return `${Math.round(props.summary.successRate * 1000) / 10}%`
})

const numberFormat = new Intl.NumberFormat('uz-UZ')

function fmt(value: number | undefined): string {
  return value === undefined ? '-' : numberFormat.format(value)
}
</script>

<template>
  <div class="kpi-grid">
    <div class="card kpi">
      <span class="kpi-label">Jami varaqlar</span>
      <span class="kpi-value">{{ fmt(summary?.totalPages) }}</span>
    </div>
    <div class="card kpi">
      <span class="kpi-label">Jami buyurtmalar</span>
      <span class="kpi-value">{{ fmt(summary?.totalJobs) }}</span>
    </div>
    <div class="card kpi">
      <span class="kpi-label">Muvaffaqiyat darajasi</span>
      <span class="kpi-value">{{ successPercent }}</span>
    </div>
    <div class="card kpi">
      <span class="kpi-label">Faol printerlar</span>
      <span class="kpi-value">{{ fmt(summary?.activePrinters) }}</span>
    </div>
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.kpi {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.kpi-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.kpi-value {
  font-size: 1.8rem;
  font-weight: 700;
}
</style>
