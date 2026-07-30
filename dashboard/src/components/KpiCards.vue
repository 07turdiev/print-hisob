<script setup lang="ts">
import { computed } from 'vue'
import type { StatsSummary } from '../api/types'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ summary: StatsSummary | null }>()

const successPercent = computed(() => {
  if (!props.summary) return '-'
  return `${Math.round(props.summary.successRate * 1000) / 10}%`
})

const numberFormat = new Intl.NumberFormat('uz-UZ')

function fmt(value: number | undefined): string {
  return value === undefined ? '-' : numberFormat.format(value)
}

const tiles = computed(() => [
  { label: 'Jami varaqlar', value: fmt(props.summary?.totalPages), icon: 'document' },
  { label: 'Jami buyurtmalar', value: fmt(props.summary?.totalJobs), icon: 'layers' },
  { label: 'Muvaffaqiyat darajasi', value: successPercent.value, icon: 'check-circle' },
  { label: 'Faol printerlar', value: fmt(props.summary?.activePrinters), icon: 'printers' },
])
</script>

<template>
  <div class="kpi-grid">
    <div v-for="tile in tiles" :key="tile.label" class="card kpi">
      <span class="kpi-icon">
        <AppIcon :name="tile.icon" :size="18" />
      </span>
      <div class="kpi-body">
        <span class="kpi-label">{{ tile.label }}</span>
        <span class="kpi-value">{{ tile.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.kpi {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

.kpi-icon {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: var(--radius-sm);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent-soft-fg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-body {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.kpi-label {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.kpi-value {
  font-size: 1.65rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
</style>
