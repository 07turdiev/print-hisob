import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  ApiError,
  getEmployeeStats,
  getFailures,
  getSummary,
  getTimeseries,
  getTopStats,
  putQuotas,
} from '../api/client'
import type {
  EmployeeStat,
  FailureReason,
  StatsSummary,
  TimeseriesPoint,
  TopStats,
} from '../api/types'
import { usePeriodStore } from '../stores/period'

/**
 * Loads every /api/stats/* panel for the currently selected period and keeps
 * them in sync whenever year/periodNo/periodType changes. The department
 * filter is applied client-side to the employee list, since the backend does
 * not support filtering these aggregate endpoints by department.
 */
export function useDashboardData() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo, department } = storeToRefs(periodStore)

  const summary = ref<StatsSummary | null>(null)
  const employees = ref<EmployeeStat[]>([])
  const timeseries = ref<TimeseriesPoint[]>([])
  const topStats = ref<TopStats | null>(null)
  const failures = ref<FailureReason[]>([])

  const loading = ref(false)
  const error = ref<string | null>(null)

  async function reload() {
    loading.value = true
    error.value = null
    // The department filter is applied client-side below (not sent to the
    // server) so the dropdown option list keeps showing every available choice.
    const params = { periodType: periodType.value, year: year.value, periodNo: periodNo.value }
    try {
      const [summaryRes, employeesRes, timeseriesRes, topRes, failuresRes] = await Promise.all([
        getSummary(params),
        getEmployeeStats(params),
        getTimeseries(params),
        getTopStats(params),
        getFailures(params),
      ])
      summary.value = summaryRes
      employees.value = employeesRes
      timeseries.value = timeseriesRes
      topStats.value = topRes
      failures.value = failuresRes
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Maʻlumotlarni yuklab boʻlmadi'
    } finally {
      loading.value = false
    }
  }

  watch([periodType, year, periodNo], reload, { immediate: true })

  /** Saves one employee's quota via PUT /api/quotas and patches the local list in place. */
  async function saveQuota(login: string, allocatedPages: number) {
    const [saved] = await putQuotas({
      login,
      periodType: periodType.value,
      year: year.value,
      periodNo: periodNo.value,
      allocatedPages,
    })
    const target = employees.value.find((emp) => emp.login === login)
    if (target && saved) {
      target.allocated = saved.allocatedPages
      target.remaining = target.allocated - target.used
      target.overLimit = target.used > target.allocated
    }
  }

  const departmentOptions = computed(() => {
    const set = new Set<string>()
    for (const emp of employees.value) {
      if (emp.department) set.add(emp.department)
    }
    return Array.from(set).sort()
  })

  const filteredEmployees = computed(() =>
    employees.value.filter((emp) => {
      if (department.value && emp.department !== department.value) return false
      return true
    }),
  )

  const unmatchedEmployees = computed(() =>
    filteredEmployees.value.filter((emp) => emp.matchStatus === 'unmatched'),
  )

  return {
    summary,
    employees: filteredEmployees,
    allEmployees: employees,
    unmatchedEmployees,
    timeseries,
    topStats,
    failures,
    loading,
    error,
    departmentOptions,
    reload,
    saveQuota,
  }
}
