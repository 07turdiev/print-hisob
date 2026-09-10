<script setup lang="ts">
import { computed } from 'vue'
import type { AdSyncStatus } from '../api/types'
import { formatRelativeMinutes } from '../utils/time'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ status: AdSyncStatus | null }>()

const dateTimeFormat = new Intl.DateTimeFormat('uz-UZ', { dateStyle: 'medium', timeStyle: 'short' })

const relative = computed(() => formatRelativeMinutes(props.status?.minutesSinceSync ?? null))

const absoluteTitle = computed(() => {
  if (!props.status?.lastSyncedAt) return ''
  try {
    return `Oxirgi sinxronizatsiya: ${dateTimeFormat.format(new Date(props.status.lastSyncedAt))}`
  } catch {
    return props.status.lastSyncedAt
  }
})

/** Sinxron eskirgan bo'lsa ogohlantiruvchi, aks holda axborot ko'rinishi. */
const tone = computed(() => {
  const status = props.status
  if (!status) return 'info'
  return status.isStale || status.employeeCount === 0 ? 'warning' : 'info'
})

const message = computed(() => {
  const status = props.status
  if (!status) return ''
  if (status.employeeCount === 0) {
    return "Hali hech qanday xodim yuklanmagan — AD sinxronizatsiyasini ishga tushiring."
  }
  if (status.isStale) {
    return `AD sinxronizatsiyasi to'xtagan bo'lishi mumkin — oxirgi ma'lumot ${relative.value}. Windows'dagi 'PrinterHisob-AdSync' vazifasini tekshiring.`
  }
  return `AD sinxronizatsiyasi normal: oxirgi ma'lumot ${relative.value}, ${status.activeCount} ta faol xodim.`
})
</script>

<template>
  <div v-if="status" class="alert" :class="`alert--${tone}`" :title="absoluteTitle">
    <span class="alert__icon">
      <AppIcon :name="tone === 'warning' ? 'warning' : 'refresh'" :size="16" />
    </span>
    <span>{{ message }}</span>
  </div>
</template>
