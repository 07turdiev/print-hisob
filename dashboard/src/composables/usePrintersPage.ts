import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError, getPrinterStats, renamePrinter } from '../api/client'
import type { PrinterStat } from '../api/types'
import { usePeriodStore } from '../stores/period'

export function usePrintersPage() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo } = storeToRefs(periodStore)

  const printers = ref<PrinterStat[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  /** Per-mac rename state: which row is currently being saved and its last error, if any. */
  const savingMac = ref<string | null>(null)
  const renameErrors = reactive<Record<string, string>>({})

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

  /** Renames a printer (mac must be non-null — legacy printers can't be renamed) and
   *  patches the row in place on success so the table/chart reflect the new name at once. */
  async function rename(mac: string, name: string) {
    savingMac.value = mac
    delete renameErrors[mac]
    try {
      const updated = await renamePrinter(mac, name)
      const row = printers.value.find((p) => p.mac === mac)
      if (row) row.name = updated.displayName
    } catch (err) {
      renameErrors[mac] = err instanceof ApiError ? err.message : "Nomni saqlab bo'lmadi"
      throw err
    } finally {
      savingMac.value = null
    }
  }

  return { printers: sorted, chartItems, loading, error, savingMac, renameErrors, rename }
}
