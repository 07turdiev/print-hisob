<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ used: number; allocated: number; overLimit: boolean }>()

const percent = computed(() => {
  if (props.allocated <= 0) return props.used > 0 ? 100 : 0
  return Math.min(100, Math.round((props.used / props.allocated) * 100))
})
</script>

<template>
  <div class="usage-bar">
    <div class="usage-row">
      <span>{{ used }} / {{ allocated }}</span>
      <span :class="{ negative: overLimit }">{{ allocated > 0 ? Math.round((used / allocated) * 100) : '-' }}%</span>
    </div>
    <div class="bar-track">
      <div class="bar-fill" :class="{ over: overLimit }" :style="{ width: `${percent}%` }" />
    </div>
  </div>
</template>

<style scoped>
.usage-bar {
  min-width: 9rem;
}

.usage-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.82rem;
  margin-bottom: 0.3rem;
  font-variant-numeric: tabular-nums;
}

.negative {
  color: var(--color-danger-fg);
  font-weight: 700;
}

.bar-track {
  height: 8px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-2);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--brand-gradient);
  transition: width var(--transition);
}

.bar-fill.over {
  background: var(--color-danger-fg);
}
</style>
