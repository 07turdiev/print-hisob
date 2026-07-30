import { ref } from 'vue'
import { ApiError, getAdSyncStatus } from '../api/client'
import type { AdSyncStatus } from '../api/types'

/**
 * Loads the AD sync health indicator (GET /api/ad-sync/status), shared by the Xodimlar
 * page banner and the Bosh sahifa stale-warning highlight. The data only changes hourly
 * server-side, so a single fetch on mount is enough — no polling needed.
 */
export function useAdSyncStatus() {
  const status = ref<AdSyncStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function reload() {
    loading.value = true
    error.value = null
    try {
      status.value = await getAdSyncStatus()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "AD holatini yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  reload()

  return { status, loading, error, reload }
}
