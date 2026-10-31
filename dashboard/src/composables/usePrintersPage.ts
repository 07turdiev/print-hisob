import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError, getPrinterStats, mergePrinters, renamePrinter } from '../api/client'
import type { PrinterStat } from '../api/types'
import { usePeriodStore } from '../stores/period'

/**
 * Printerlar sahifasi.
 *
 * Qator kaliti — reyestrdagi qurilma id'si (`deviceId`). Chop etish yozuvi
 * qurilmaga MAC -> IP -> drayver nomi tartibida bog'lanadi, shuning uchun bitta
 * jismoniy printer turli kompyuterlarda turlicha atalgan bo'lsa ham bitta
 * qatorga tushadi. Agar baribir ikki qator bo'lib qolsa (masalan ikki xil IP
 * bilan ko'ringan), ularni `merge` birlashtiradi.
 */
export function usePrintersPage() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo } = storeToRefs(periodStore)

  const printers = ref<PrinterStat[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  /** Qaysi qator saqlanmoqda va unda qanday xato bo'lgani (qurilma id'si bo'yicha). */
  const savingId = ref<number | null>(null)
  const rowErrors = reactive<Record<number, string>>({})

  async function reload() {
    loading.value = true
    error.value = null
    try {
      printers.value = await getPrinterStats({
        periodType: periodType.value,
        year: year.value,
        periodNo: periodNo.value,
      })
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  watch([periodType, year, periodNo], reload, { immediate: true })

  const sorted = computed(() => [...printers.value].sort((a, b) => b.pages - a.pages))
  const chartItems = computed(() => sorted.value.map((p) => ({ name: p.name, value: p.pages })))

  function describe(err: unknown, fallback: string): string {
    if (err instanceof ApiError) return err.detail ?? err.message
    return fallback
  }

  /** Nom qo'yadi va qatorni joyida yangilaydi — jadval va diagramma darhol mos keladi. */
  async function rename(deviceId: number, name: string) {
    savingId.value = deviceId
    delete rowErrors[deviceId]
    try {
      const updated = await renamePrinter(deviceId, name)
      const row = printers.value.find((p) => p.deviceId === deviceId)
      if (row) row.name = updated.displayName
    } catch (err) {
      rowErrors[deviceId] = describe(err, "Nomni saqlab bo'lmadi")
      throw err
    } finally {
      savingId.value = null
    }
  }

  /**
   * `sourceId` printerini `targetId` ichiga qo'shadi.
   *
   * Birlashtirishdan keyin ikkala qatorning sarfi qo'shiladi, shuning uchun
   * ro'yxat to'liq qayta yuklanadi — joyida tuzatib bo'lmaydi.
   */
  async function merge(targetId: number, sourceId: number) {
    savingId.value = sourceId
    delete rowErrors[sourceId]
    try {
      await mergePrinters(targetId, sourceId)
      await reload()
    } catch (err) {
      rowErrors[sourceId] = describe(err, "Printerlarni birlashtirib bo'lmadi")
      throw err
    } finally {
      savingId.value = null
    }
  }

  return { printers: sorted, chartItems, loading, error, savingId, rowErrors, rename, merge, reload }
}
