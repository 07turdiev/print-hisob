import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  ApiError,
  getPrinterStats,
  getPrinterSuggestions,
  mergePrinters,
  renamePrinter,
} from '../api/client'
import type { PrinterMergeSuggestion, PrinterStat } from '../api/types'
import { usePeriodStore } from '../stores/period'

/** Jadval qatori: statistika + (bo'lsa) birlashtirish taklifi. */
export interface PrinterRow extends PrinterStat {
  suggestion: PrinterMergeSuggestion | null
}

/**
 * Printerlar sahifasi.
 *
 * Qator kaliti — reyestrdagi qurilma id'si (`deviceId`). Chop etish yozuvi
 * qurilmaga MAC -> IP -> drayver nomi tartibida bog'lanadi, shuning uchun bitta
 * jismoniy printer turli kompyuterlarda turlicha atalgan bo'lsa ham bitta
 * qatorga tushadi. Agar baribir ikki qator bo'lib qolsa (masalan ikki xil IP
 * bilan ko'ringan), ularni `merge` birlashtiradi.
 *
 * Taklif ro'yxati (`suggestionFor`) davrga bog'liq emas — u butun tarix bo'yicha
 * hisoblanadi, shuning uchun davr almashganda qayta so'ralmaydi.
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

  const suggestions = ref<PrinterMergeSuggestion[]>([])

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

  /**
   * Takliflar alohida yuklanadi va xatosi jim o'tadi: ular qo'shimcha yordam,
   * ularsiz ham sahifa to'liq ishlaydi.
   */
  async function reloadSuggestions() {
    try {
      suggestions.value = await getPrinterSuggestions()
    } catch {
      suggestions.value = []
    }
  }

  watch([periodType, year, periodNo], reload, { immediate: true })
  reloadSuggestions()

  /** `deviceId` -> taklif, qatorlarga ulash uchun. */
  const byDevice = computed(() => {
    const map = new Map<number, PrinterMergeSuggestion>()
    for (const s of suggestions.value) map.set(s.deviceId, s)
    return map
  })

  const sorted = computed<PrinterRow[]>(() =>
    [...printers.value]
      .sort((a, b) => b.pages - a.pages)
      .map((p) => ({
        ...p,
        suggestion: p.deviceId !== null ? byDevice.value.get(p.deviceId) ?? null : null,
      })),
  )

  const chartItems = computed(() => sorted.value.map((p) => ({ name: p.name, value: p.pages })))

  /** Taklifda ko'rsatilgan qurilmaning ko'rinadigan nomi (jadvaldan olinadi). */
  function nameOf(deviceId: number): string {
    return printers.value.find((p) => p.deviceId === deviceId)?.name ?? `#${deviceId}`
  }

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
   * ro'yxat to'liq qayta yuklanadi — joyida tuzatib bo'lmaydi. Takliflar ham
   * qayta hisoblanadi: birlashtirish ro'yxatdagi boshqa juftlarni ham
   * o'zgartirishi mumkin.
   */
  async function merge(targetId: number, sourceId: number) {
    savingId.value = sourceId
    delete rowErrors[sourceId]
    try {
      await mergePrinters(targetId, sourceId)
      await Promise.all([reload(), reloadSuggestions()])
    } catch (err) {
      rowErrors[sourceId] = describe(err, "Printerlarni birlashtirib bo'lmadi")
      throw err
    } finally {
      savingId.value = null
    }
  }

  return {
    printers: sorted,
    chartItems,
    loading,
    error,
    savingId,
    rowErrors,
    suggestionCount: computed(() => suggestions.value.length),
    nameOf,
    rename,
    merge,
    reload,
  }
}
