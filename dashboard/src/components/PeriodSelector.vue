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
  padding: 0.35rem 0.55rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
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
}

.quarter-btn {
  padding: 0.35rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.85rem;
}

.quarter-btn.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-accent-fg);
}
</style>
