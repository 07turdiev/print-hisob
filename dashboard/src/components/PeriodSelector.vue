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
      <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
    </select>

    <div v-if="isQuarter" class="quarter-buttons">
      <button
        v-for="q in [1, 2, 3, 4]"
        :key="q"
        type="button"
        class="quarter-btn"
        :class="{ active: store.periodNo === q }"
        @click="store.setPeriodNo(q)"
      >
        Q{{ q }}
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
  gap: 0.5rem;
}

select {
  font-size: 0.85rem;
}

.year-select {
  min-width: 5rem;
}

.month-select {
  min-width: 8rem;
}

.quarter-buttons {
  display: flex;
  gap: 0.3rem;
  padding: 0.2rem;
  background: var(--color-surface-2);
  border-radius: var(--radius-sm);
}

.quarter-btn {
  height: 28px;
  padding: 0 0.7rem;
  border: none;
  border-radius: calc(var(--radius-sm) - 2px);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 600;
  transition: background-color var(--transition), color var(--transition);
}

.quarter-btn:hover {
  color: var(--color-text);
}

.quarter-btn.active {
  background: var(--color-surface);
  color: var(--color-accent-soft-fg);
  box-shadow: var(--shadow-sm);
}
</style>
