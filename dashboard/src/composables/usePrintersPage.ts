import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError, getPrinterStats } from '../api/client'
import type { PrinterStat } from '../api/types'
import { usePeriodStore } from '../stores/period'

export function usePrintersPage() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo } = storeToRefs(periodStore)

  const printers = ref<PrinterStat[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function reload() {
    loading.value = true
    error.value = null
    try {
      printers.value = await getPrinterStats({ periodType: periodType.value, year: year.value, periodNo: periodNo.value })
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  watch([periodType, year, periodNo], reload, { immediate: true })

  const sorted = computed(() => [...printers.value].sort((a, b) => b.pages - a.pages))
  const chartItems = computed(() => sorted.value.map((p) => ({ name: p.name, value: p.pages })))

  return { printers: sorted, chartItems, loading, error }
}
