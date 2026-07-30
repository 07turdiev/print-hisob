<script setup lang="ts">
import type { PeriodType } from '../api/types'
import { useCsvDownload } from '../composables/useCsvDownload'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  periodType: PeriodType
  year: number
  periodNo: number
  department?: string
}>()

const { downloading, downloadError, downloadCsv } = useCsvDownload()

function handleClick() {
  downloadCsv({
    periodType: props.periodType,
    year: props.year,
    periodNo: props.periodNo,
    department: props.department || undefined,
  })
}
</script>

<template>
  <div class="csv-download">
    <button type="button" class="btn btn-sm csv-btn" :disabled="downloading" @click="handleClick">
      <AppIcon name="download" :size="15" />
      {{ downloading ? 'Yuklanmoqda...' : 'CSV yuklab olish' }}
    </button>
    <span v-if="downloadError" class="csv-error">{{ downloadError }}</span>
  </div>
</template>

<style scoped>
.csv-download {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.csv-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-soft-bg);
}

.csv-error {
  color: var(--color-danger-fg);
  font-size: 0.8rem;
}
</style>
