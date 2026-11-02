import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError, getPolicyViolations } from '../api/client'
import type { PolicyViolation } from '../api/types'
import { usePeriodStore } from '../stores/period'

/**
 * Guruh siyosatini buzib chiqarilgan qog'oz.
 *
 * Agent hali `allowedPrinters` ni bilmagani uchun "faqat belgilangan" siyosati
 * jismonan to'smaydi — bu hisobot hozircha yagona nazorat vositasi. Agent
 * yangilangandan keyin ham kerak bo'ladi: eski versiyada qolgan mashinalarni
 * ko'rsatib beradi.
 */
export function usePolicyViolations() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo } = storeToRefs(periodStore)

  const rows = ref<PolicyViolation[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function reload() {
    loading.value = true
    error.value = null
    try {
      rows.value = await getPolicyViolations({
        periodType: periodType.value,
        year: year.value,
        periodNo: periodNo.value,
      })
    } catch (err) {
      error.value =
        err instanceof ApiError ? (err.detail ?? err.message) : "Hisobotni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  watch([periodType, year, periodNo], reload, { immediate: true })

  const totalPages = computed(() => rows.value.reduce((sum, r) => sum + r.pages, 0))
  /** Nechta xodim buzgani — qatorlar soni emas, odamlar soni. */
  const peopleCount = computed(() => new Set(rows.value.map((r) => r.login)).size)

  return { rows, totalPages, peopleCount, loading, error, reload }
}
