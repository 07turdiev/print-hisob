<script setup lang="ts">
import { computed } from 'vue'
import { usePeriodStore } from '../stores/period'

const store = usePeriodStore()

const MONTH_NAMES = [
  'Yanvar',
  'Fevral',
  'Mart',
  'Aprel',
  'May',
  'Iyun',
  'Iyul',
  'Avgust',
  'Sentyabr',
  'Oktyabr',
  'Noyabr',
  'Dekabr',
]

const years = computed(() => {
  const current = new Date().getFullYear()
  const list: number[] = []
  for (let y = current + 1; y >= current - 4; y--) list.push(y)
  return list
})

const isQuarter = computed(() => store.periodType === 'quarter')
</script>

<template>
  <div class="period-selector">
    <select
      class="year-select"
      :value="store.year"
      title="Yil"
      @change="store.setYear(Number(($event.target as HTMLSelectElement).value))"
    >
      <option v-for="y in years" :key="y" :value="y">{{ y }}-yil</option>
    </select>

    <!-- Choraklar bo'lingan tugmalar (segment) ko'rinishida -->
    <div v-if="isQuarter" class="segments" role="group" aria-label="Chorak">
      <button
        v-for="q in [1, 2, 3, 4]"
        :key="q"
        type="button"
        class="segment"
        :class="{ active: store.periodNo === q }"
        :title="`${q}-chorak`"
        @click="store.setPeriodNo(q)"
      >
        {{ q }}-ch
      </button>
    </div>

    <select
      v-else
      class="month-select"
      title="Oy"
      :value="store.periodNo"
      @change="store.setPeriodNo(Number(($event.target as HTMLSelectElement).value))"
    >
      <option v-for="(name, idx) in MONTH_NAMES" :key="name" :value="idx + 1">{{ name }}</option>
    </select>
  </div>
</template>

<style scoped>
.period-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.year-select {
  min-width: 6.2rem;
}

.month-select {
  min-width: 8rem;
}

.segments {
  display: flex;
  height: 32px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface);
}

.segment {
  min-width: 2.9rem;
  padding: 0 8px;
  border: none;
  border-right: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 600;
  transition: background-color var(--transition), color var(--transition);
}

.segment:last-child {
  border-right: none;
}

.segment:hover:not(.active) {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.segment.active {
  background: var(--color-accent);
  color: var(--color-accent-fg);
}
</style>
