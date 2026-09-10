import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError, getEmployeeStats, getEmployees, getQuotas, getSummary, putQuotas } from '../api/client'
import type { Employee, EmployeeQuota, EmployeeStat, MergedEmployeeRow } from '../api/types'
import { usePeriodStore } from '../stores/period'
import { useAdSyncStatus } from './useAdSyncStatus'

export type ActiveFilter = '' | 'active' | 'inactive'

/**
 * Drives the Xodimlar page: merges the full AD directory (GET /api/employees) with
 * the selected period's usage/quota (GET /api/stats/employees), so every employee is
 * visible even with zero prints, while unmatched logins (usage with no AD record)
 * still show up from the stats side.
 */
export function useEmployeesPage() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo, department } = storeToRefs(periodStore)

  const search = ref('')
  const activeFilter = ref<ActiveFilter>('')

  const adEmployees = ref<Employee[]>([])
  const stats = ref<EmployeeStat[]>([])
  const quotas = ref<EmployeeQuota[]>([])
  /** Default quota (pages) for the selected period, used when an employee has neither
   *  a stats row (no prints) nor an explicit quota row — keeps this page in sync with
   *  what the backend applies everywhere else instead of falling back to a hardcoded 0. */
  const defaultQuota = ref(0)
  /** Unfiltered directory snapshot, used only to populate the department dropdown. */
  const directoryOptions = ref<Employee[]>([])
  /** AD sync health, shown as a banner at the top of the page; independent of the selected period. */
  const { status: adSyncStatus } = useAdSyncStatus()

  const loading = ref(false)
  const error = ref<string | null>(null)

  let searchTimer: ReturnType<typeof setTimeout> | undefined

  async function reload() {
    loading.value = true
    error.value = null
    try {
      const periodParams = { periodType: periodType.value, year: year.value, periodNo: periodNo.value }
      const [adRes, statsRes, quotasRes, summaryRes] = await Promise.all([
        getEmployees({
          department: department.value || undefined,
          q: search.value || undefined,
          isActive: activeFilter.value === '' ? undefined : activeFilter.value === 'active',
          limit: 1000,
        }),
        getEmployeeStats(periodParams),
        getQuotas(periodParams),
        getSummary(periodParams),
      ])
      adEmployees.value = adRes
      stats.value = statsRes
      quotas.value = quotasRes
      defaultQuota.value = summaryRes.defaultQuota
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  async function loadDirectoryOptions() {
    try {
      directoryOptions.value = await getEmployees({ limit: 1000 })
    } catch {
      // Non-critical: dropdown just stays empty if this fails.
    }
  }

  function scheduleReload() {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(reload, 300)
  }

  watch([periodType, year, periodNo, department, activeFilter], reload, { immediate: true })
  watch(search, scheduleReload)
  loadDirectoryOptions()

  /**
   * AD ro'yxati (`/api/employees`) serverda filtrlanadi, sarf statistikasi
   * (`/api/stats/employees`) esa har doim to'liq keladi. Quyidagi birlashtirishda
   * statistikada bor, lekin filtrlangan AD ro'yxatida yo'q qatorlar qo'shiladi —
   * ular ham xuddi shu filtrlardan o'tishi shart, aks holda tanlangan bo'lim,
   * qidiruv va holat filtrlari butunlay chetlab o'tiladi.
   */
  function statRowPassesFilters(stat: EmployeeStat): boolean {
    // Bo'lim filtri: bu qatorlar yo AD'da umuman yo'q (bo'limi ham yo'q), yo
    // boshqa bo'limga tegishli — ikkala holatda ham mos kelmaydi. Backend
    // `/api/stats/employees?department=...` da aynan shunday ishlaydi.
    if (department.value) return false
    // Holat filtri: AD'da topilmagan login faol ham, ketgan ham emas.
    if (activeFilter.value) return false

    const query = search.value.trim().toLowerCase()
    if (!query) return true
    return (
      stat.login.toLowerCase().includes(query) ||
      (stat.fullName ?? '').toLowerCase().includes(query)
    )
  }

  const rows = computed<MergedEmployeeRow[]>(() => {
    const statMap = new Map(stats.value.map((s) => [s.login, s]))
    const quotaMap = new Map(quotas.value.map((q) => [q.login, q.allocatedPages]))
    const seen = new Set<string>()
    const result: MergedEmployeeRow[] = []

    for (const emp of adEmployees.value) {
      seen.add(emp.login)
      const stat = statMap.get(emp.login)
      const used = stat?.used ?? 0
      const allocated = stat?.allocated ?? quotaMap.get(emp.login) ?? defaultQuota.value
      result.push({
        login: emp.login,
        fullName: emp.fullName,
        department: emp.department,
        position: emp.position ?? stat?.position ?? null,
        used,
        allocated,
        remaining: allocated - used,
        overLimit: stat?.overLimit ?? used > allocated,
        matchStatus: emp.isActive ? 'active' : 'inactive',
      })
    }

    // Sarfi bor, lekin filtrlangan AD ro'yxatiga tushmagan loginlar — odatda
    // AD'da umuman topilmaganlar (unmatched). Faqat joriy filtrlarga mos
    // kelganlari qo'shiladi.
    for (const stat of stats.value) {
      if (seen.has(stat.login)) continue
      if (!statRowPassesFilters(stat)) continue
      result.push({
        login: stat.login,
        fullName: stat.fullName,
        department: stat.department,
        position: stat.position,
        used: stat.used,
        allocated: stat.allocated,
        remaining: stat.remaining,
        overLimit: stat.overLimit,
        matchStatus: stat.matchStatus,
      })
    }

    return result
  })

  const departmentOptions = computed(() => {
    const set = new Set<string>()
    for (const emp of directoryOptions.value) if (emp.department) set.add(emp.department)
    return Array.from(set).sort()
  })

  async function saveQuota(login: string, allocatedPages: number) {
    const [saved] = await putQuotas({
      login,
      periodType: periodType.value,
      year: year.value,
      periodNo: periodNo.value,
      allocatedPages,
    })
    if (!saved) return

    const existingQuota = quotas.value.find((q) => q.login === login)
    if (existingQuota) {
      existingQuota.allocatedPages = saved.allocatedPages
    } else {
      quotas.value.push(saved)
    }

    const stat = stats.value.find((s) => s.login === login)
    if (stat) {
      stat.allocated = saved.allocatedPages
      stat.remaining = stat.allocated - stat.used
      stat.overLimit = stat.used > stat.allocated
    }
  }

  return {
    rows,
    search,
    activeFilter,
    departmentOptions,
    defaultQuota,
    adSyncStatus,
    loading,
    error,
    saveQuota,
  }
}
