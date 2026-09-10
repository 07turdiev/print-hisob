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
    <span v-if="downloadError" class="csv-error">{{ downloadError }}</span>
    <button
      type="button"
      class="btn btn-sm"
      :disabled="downloading"
      title="KPI shaklidagi hisobotni Excel uchun yuklab olish"
      @click="handleClick"
    >
      <AppIcon name="download" :size="14" />
      {{ downloading ? 'Tayyorlanmoqda...' : 'CSV yuklab olish' }}
    </button>
  </div>
</template>

<style scoped>
.csv-download {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.csv-error {
  color: var(--color-danger-fg);
  font-size: var(--font-size-xs);
}
</style>
