import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  ApiError,
  getDepartmentStats,
  getEmployeeStats,
  getFailures,
  getSummary,
  getTimeseries,
  getTopStats,
  putQuotas,
} from '../api/client'
import type {
  DepartmentStat,
  EmployeeStat,
  FailureReason,
  StatsSummary,
  TimeseriesPoint,
  TopStats,
} from '../api/types'
import { usePeriodStore } from '../stores/period'

/**
 * Loads every /api/stats/* panel for the currently selected period and keeps them in
 * sync whenever year/periodNo/periodType/department changes.
 *
 * Bo'lim filtri **serverga** yuboriladi — shunda KPI kartochkalari, grafik, top
 * ro'yxatlar va xatoliklar ham tanlangan bo'lim bo'yicha hisoblanadi. (Ilgari filtr
 * faqat jadvalga qo'llanardi va yuqoridagi raqamlar butun tashkilotniki bo'lib
 * qolardi — bu chalg'ituvchi edi.)
 */
export function useDashboardData() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo, department } = storeToRefs(periodStore)

  const summary = ref<StatsSummary | null>(null)
  const employees = ref<EmployeeStat[]>([])
  const timeseries = ref<TimeseriesPoint[]>([])
  const topStats = ref<TopStats | null>(null)
  const failures = ref<FailureReason[]>([])
  /** Filtrsiz bo'limlar ro'yxati — tanlov ro'yxati filtr tufayli qisqarib qolmasligi uchun. */
  const departments = ref<DepartmentStat[]>([])

  const loading = ref(false)
  const error = ref<string | null>(null)

  async function reload() {
    loading.value = true
    error.value = null

    const period = { periodType: periodType.value, year: year.value, periodNo: periodNo.value }
    const params = { ...period, department: department.value || undefined }

    try {
      const [summaryRes, employeesRes, timeseriesRes, topRes, failuresRes, departmentsRes] =
        await Promise.all([
          getSummary(params),
          getEmployeeStats(params),
          getTimeseries(params),
          getTopStats(params),
          getFailures(params),
          // Ataylab `params` emas, `period`: tanlov ro'yxati har doim to'liq bo'lishi
          // kerak, aks holda bo'lim tanlangach boshqasiga o'tib bo'lmay qoladi.
          getDepartmentStats(period),
        ])
      summary.value = summaryRes
      employees.value = employeesRes
      timeseries.value = timeseriesRes
      topStats.value = topRes
      failures.value = failuresRes
      departments.value = departmentsRes
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  watch([periodType, year, periodNo, department], reload, { immediate: true })

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

  const departmentOptions = computed(() =>
    departments.value
      .map((d) => d.name)
      .filter(Boolean)
      .sort(),
  )

  /** AD'da topilmagan loginlar. Bo'lim filtri faol bo'lsa server ularni allaqachon
   *  chiqarib tashlagan bo'ladi (bo'limi yo'q), shuning uchun ro'yxat bo'sh bo'ladi. */
  const unmatchedEmployees = computed(() =>
    employees.value.filter((emp) => emp.matchStatus === 'unmatched'),
  )

  return {
    summary,
    employees,
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
