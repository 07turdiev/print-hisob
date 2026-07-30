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
    return dateTimeFormat.format(new Date(props.status.lastSyncedAt))
  } catch {
    return props.status.lastSyncedAt
  }
})

const message = computed(() => {
  const status = props.status
  if (!status) return ''
  if (status.employeeCount === 0) {
    return "⚠️ Hali hech qanday xodim yuklanmagan — AD sinxronizatsiyasini ishga tushiring."
  }
  if (status.isStale) {
    return `⚠️ AD sinxronizatsiyasi to'xtagan bo'lishi mumkin — oxirgi ma'lumot ${relative.value}. Windows'dagi 'PrinterHisob-AdSync' vazifasini tekshiring.`
  }
  return `AD sinxron: oxirgi ma'lumot ${relative.value} (${status.activeCount} faol xodim)`
})
</script>

<template>
  <div v-if="status" class="card ad-sync-banner" :class="{ stale: status.isStale }" :title="absoluteTitle">
    <AppIcon :name="status.isStale ? 'warning' : 'refresh'" :size="16" />
    <span>{{ message }}</span>
  </div>
</template>

<style scoped>
.ad-sync-banner {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.6rem 1rem;
  font-size: 0.85rem;
  color: var(--color-accent-soft-fg);
  background: var(--color-accent-soft-bg);
  border-color: transparent;
  box-shadow: none;
}

.ad-sync-banner.stale {
  background: var(--color-warning-bg);
  color: var(--color-warning-fg);
  font-weight: 600;
}
</style>
