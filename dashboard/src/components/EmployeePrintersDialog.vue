<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ApiError, getPrinterAccess, getPrinterStats } from '../api/client'
import type { PrinterStat } from '../api/types'
import { usePeriodStore } from '../stores/period'
import { periodDateRange, periodLabel } from '../utils/period'
import AppIcon from './AppIcon.vue'

/**
 * Bitta xodim tanlangan davrda qaysi printerlardan chop etganini ko'rsatadi.
 * Ota komponent oynani `v-if` bilan ochadi, shuning uchun ma'lumot har ochilganda
 * yangidan yuklanadi.
 */
const props = defineProps<{
  employee: { login: string; fullName: string | null; department: string | null }
}>()

const emit = defineEmits<{ close: [] }>()

const periodStore = usePeriodStore()
const numberFormat = new Intl.NumberFormat('uz-UZ')
const dateTimeFormat = new Intl.DateTimeFormat('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })
const fmt = (n: number) => numberFormat.format(n)

const printers = ref<PrinterStat[]>([])
/** Umumiy printerlar: ro'yxatda "Umumiy" belgisi bilan ajratiladi. */
const publicIds = ref<Set<number>>(new Set())
const loading = ref(true)
const error = ref<string | null>(null)

const title = computed(() => `${periodStore.year}-yil, ${periodLabel(periodStore.periodType, periodStore.periodNo)}`)

const totals = computed(() => ({
  pages: printers.value.reduce((sum, p) => sum + p.pages, 0),
  jobs: printers.value.reduce((sum, p) => sum + p.jobs, 0),
}))

/** Jurnal shu xodim va shu davr bilan ochiladi. */
const journalLink = computed(() => ({
  name: 'journal',
  query: {
    user: props.employee.login,
    ...periodDateRange(periodStore.periodType, periodStore.year, periodStore.periodNo),
  },
}))

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—'
  try {
    return dateTimeFormat.format(new Date(iso))
  } catch {
    return iso
  }
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const params = {
      periodType: periodStore.periodType,
      year: periodStore.year,
      periodNo: periodStore.periodNo,
    }
    const [stats, access] = await Promise.all([
      getPrinterStats(params, props.employee.login),
      // Belgi uchun kerak, xato bo'lsa ro'yxat baribir ko'rinadi.
      getPrinterAccess().catch(() => null),
    ])
    printers.value = stats
    publicIds.value = new Set(access?.publicDeviceIds ?? [])
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
  } finally {
    loading.value = false
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  load()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="backdrop" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="employee-printers-title">
      <header class="dialog__head">
        <h2 id="employee-printers-title" class="dialog__title">
          <span class="dialog__icon"><AppIcon name="printers" :size="16" /></span>
          Ishlatgan printerlari
        </h2>
        <button type="button" class="icon-btn" title="Yopish" @click="emit('close')">
          <AppIcon name="close" :size="16" />
        </button>
      </header>

      <div class="dialog__body">
        <div class="who">
          <div class="who__name">{{ employee.fullName ?? employee.login }}</div>
          <div class="muted">
            {{ employee.login }}<template v-if="employee.department"> · {{ employee.department }}</template>
            · {{ title }}
          </div>
        </div>

        <p v-if="error" class="alert alert--danger dialog__alert">
          <span class="alert__icon"><AppIcon name="warning" :size="15" /></span>
          <span>{{ error }}</span>
        </p>

        <div v-else-if="loading" class="empty-state">Yuklanmoqda...</div>

        <div v-else-if="!printers.length" class="empty-state">
          <span class="empty-state__icon"><AppIcon name="printers" :size="18" /></span>
          Bu davrda chop etmagan
        </div>

        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Printer</th>
                <th class="num">Varaq</th>
                <th class="num">Ishlar</th>
                <th class="num">Xato</th>
                <th>Oxirgi marta</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in printers" :key="p.deviceId ?? p.name">
                <td>
                  <div class="printer-name">
                    <span class="strong">{{ p.name }}</span>
                    <span
                      v-if="p.deviceId !== null && publicIds.has(p.deviceId)"
                      class="badge badge--success"
                      title="Hamma uchun ruxsat etilgan umumiy printer"
                    >
                      Umumiy
                    </span>
                  </div>
                  <div v-if="p.lastIp" class="muted">{{ p.lastIp }}</div>
                </td>
                <td class="num strong">{{ fmt(p.pages) }}</td>
                <td class="num">{{ fmt(p.jobs) }}</td>
                <td class="num">
                  <span v-if="p.failedJobs" class="negative">{{ fmt(p.failedJobs) }}</span>
                  <span v-else class="muted">—</span>
                </td>
                <td class="nowrap">{{ formatTimestamp(p.lastPrintedAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="hint">
          Faqat xodimning o'z chop etishlari. Unga biriktirilgan xodimlarniki, bekor qilingan
          ishlar va PDF kabi virtual printerlar bu yerda hisobga olinmaydi.
        </p>
      </div>

      <footer class="dialog__foot">
        <span v-if="printers.length">
          Jami: <strong>{{ fmt(totals.pages) }}</strong> varaq, {{ fmt(totals.jobs) }} ta ish,
          {{ printers.length }} ta printer
        </span>
        <span v-else />
        <RouterLink :to="journalLink" class="btn btn-ghost btn-sm" @click="emit('close')">
          Jurnalda ko'rish
          <AppIcon name="arrow-right" :size="14" />
        </RouterLink>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 30, 55, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  z-index: 50;
}

.dialog {
  width: 100%;
  max-width: 46rem;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
}

.dialog__head,
.dialog__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 9px var(--space-4);
  background: var(--color-surface-2);
}

.dialog__head {
  border-bottom: 1px solid var(--color-border);
  border-radius: var(--radius) var(--radius) 0 0;
}

.dialog__foot {
  border-top: 1px solid var(--color-border);
  border-radius: 0 0 var(--radius) var(--radius);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  flex-wrap: wrap;
}

.dialog__foot strong {
  color: var(--color-text);
}

.dialog__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.dialog__icon {
  display: inline-flex;
  color: var(--color-accent);
}

.dialog__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  min-height: 0;
  overflow-y: auto;
}

.dialog__alert {
  margin: 0;
}

.who__name {
  font-size: var(--font-size-md);
  font-weight: 600;
}

.table-wrap {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.printer-name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
</style>
