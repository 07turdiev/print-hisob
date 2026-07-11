import { ref } from 'vue'
import { ApiError, downloadEmployeesCsv } from '../api/client'
import type { PeriodParams } from '../api/types'

/**
 * Shared loading/error state for the "CSV yuklab olish" (KPI report) button,
 * used on the Xodimlar page and both report pages (Choraklik/Oylik).
 */
export function useCsvDownload() {
  const downloading = ref(false)
  const downloadError = ref<string | null>(null)

  async function downloadCsv(params: PeriodParams) {
    downloading.value = true
    downloadError.value = null
    try {
      await downloadEmployeesCsv(params)
    } catch (err) {
      downloadError.value = err instanceof ApiError ? err.message : "CSV faylni yuklab bo'lmadi"
    } finally {
      downloading.value = false
    }
  }

  return { downloading, downloadError, downloadCsv }
}
