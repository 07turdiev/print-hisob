<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ used: number; allocated: number; overLimit: boolean }>()

/** Kvotaning necha foizi ishlatilgani; kvota 0 bo'lsa va sarf bo'lsa — to'liq. */
const ratio = computed(() => {
  if (props.allocated <= 0) return props.used > 0 ? 1 : 0
  return props.used / props.allocated
})

const percentLabel = computed(() =>
  props.allocated > 0 ? `${Math.round(ratio.value * 100)}%` : '—',
)

const width = computed(() => `${Math.min(100, Math.round(ratio.value * 100))}%`)

/** 80% dan oshsa sariq, limitdan oshsa qizil — rang bilan ogohlantiramiz. */
const fillClass = computed(() => {
  if (props.overLimit || ratio.value > 1) return 'bar-fill--danger'
  if (ratio.value >= 0.8) return 'bar-fill--warning'
  return ''
})

const numberFormat = new Intl.NumberFormat('uz-UZ')
const fmt = (n: number) => numberFormat.format(n)
</script>

<template>
  <div class="usage">
    <div class="usage__row">
      <span class="usage__numbers">
        <strong>{{ fmt(used) }}</strong>
        <span class="usage__sep">/</span>
        <span>{{ fmt(allocated) }}</span>
      </span>
      <span class="usage__percent" :class="{ negative: overLimit }">{{ percentLabel }}</span>
    </div>
    <div class="bar-track">
      <div class="bar-fill" :class="fillClass" :style="{ width }" />
    </div>
  </div>
</template>

<style scoped>
.usage {
  min-width: 9rem;
}

.usage__row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}

.usage__sep {
  color: var(--color-border-strong);
  margin: 0 2px;
}

.usage__numbers span {
  color: var(--color-text-muted);
}

.usage__percent {
  font-weight: 600;
  color: var(--color-text-muted);
}
</style>
