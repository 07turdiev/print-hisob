import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError, getDepartmentStats, getEmployeeStats, getSummary, getTimeseries } from '../api/client'
import type { DepartmentStat, EmployeeStat, StatsSummary, TimeseriesPoint } from '../api/types'
import { usePeriodStore } from '../stores/period'
import { useAdSyncStatus } from './useAdSyncStatus'

/** Loads the compact overview panel shown on the Bosh sahifa (home) page. */
export function useHomeData() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo } = storeToRefs(periodStore)

  const summary = ref<StatsSummary | null>(null)
  const timeseries = ref<TimeseriesPoint[]>([])
  const employees = ref<EmployeeStat[]>([])
  const departments = ref<DepartmentStat[]>([])
  /** AD sync health; independent of the selected period, fetched once on load. */
  const { status: adSyncStatus } = useAdSyncStatus()

  const loading = ref(false)
  const error = ref<string | null>(null)

  async function reload() {
    loading.value = true
    error.value = null
    const params = { periodType: periodType.value, year: year.value, periodNo: periodNo.value }
    try {
      const [summaryRes, timeseriesRes, employeesRes, departmentsRes] = await Promise.all([
        getSummary(params),
        getTimeseries(params),
        getEmployeeStats(params),
        getDepartmentStats(params),
      ])
      summary.value = summaryRes
      timeseries.value = timeseriesRes
      employees.value = employeesRes
      departments.value = departmentsRes
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  watch([periodType, year, periodNo], reload, { immediate: true })

  const overLimitCount = computed(() => employees.value.filter((e) => e.overLimit).length)
  const unmatchedCount = computed(() => employees.value.filter((e) => e.matchStatus === 'unmatched').length)
  const topDepartment = computed<DepartmentStat | null>(() => {
    if (!departments.value.length) return null
    return [...departments.value].sort((a, b) => b.pages - a.pages)[0]
  })

  return { summary, timeseries, overLimitCount, unmatchedCount, topDepartment, adSyncStatus, loading, error }
}
