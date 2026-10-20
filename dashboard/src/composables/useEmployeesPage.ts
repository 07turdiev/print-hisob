import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  ApiError,
  getEmployeeStats,
  getEmployees,
  getQuotas,
  getSummary,
  getUserOverrides,
  putQuotas,
  setUserOverride,
} from '../api/client'
import type {
  Employee,
  EmployeeQuota,
  EmployeeStat,
  MergedEmployeeRow,
  UserOverride,
  UserOverrideInput,
} from '../api/types'
import { usePeriodStore } from '../stores/period'
import { normalizeLogin } from '../utils/logins'
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
  /** Admin qo'lda belgilagan bloklash/biriktirish holatlari. */
  const overrides = ref<UserOverride[]>([])
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
      const [adRes, statsRes, quotasRes, summaryRes, overridesRes] = await Promise.all([
        getEmployees({
          department: department.value || undefined,
          q: search.value || undefined,
          isActive: activeFilter.value === '' ? undefined : activeFilter.value === 'active',
          limit: 1000,
        }),
        getEmployeeStats(periodParams),
        getQuotas(periodParams),
        getSummary(periodParams),
        getUserOverrides(),
      ])
      adEmployees.value = adRes
      stats.value = statsRes
      quotas.value = quotasRes
      defaultQuota.value = summaryRes.defaultQuota
      overrides.value = overridesRes
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
    // Barcha xaritalar normallashtirilgan login bo'yicha — chop etish yozuvidagi
    // yozilish AD'dagidan registr yoki domen prefiksi bilan farq qilishi mumkin.
    const statMap = new Map(stats.value.map((s) => [normalizeLogin(s.login), s]))
    const quotaMap = new Map(quotas.value.map((q) => [normalizeLogin(q.login), q.allocatedPages]))
    const overrideMap = new Map(overrides.value.map((o) => [normalizeLogin(o.login), o]))
    const seen = new Set<string>()
    const result: MergedEmployeeRow[] = []

    for (const emp of adEmployees.value) {
      const key = normalizeLogin(emp.login)
      seen.add(key)
      const stat = statMap.get(key)
      const override = overrideMap.get(key)
      const used = stat?.used ?? 0
      const usedFromLinked = stat?.usedFromLinked ?? 0
      const usedTotal = used + usedFromLinked
      const allocated = stat?.allocated ?? quotaMap.get(key) ?? defaultQuota.value
      result.push({
        login: emp.login,
        fullName: emp.fullName,
        department: emp.department,
        position: emp.position ?? stat?.position ?? null,
        used,
        usedFromLinked,
        usedTotal,
        allocated,
        remaining: allocated - usedTotal,
        overLimit: stat?.overLimit ?? usedTotal > allocated,
        matchStatus: emp.isActive ? 'active' : 'inactive',
        // Hech qachon chop etmagan xodim uchun statistika qatori bo'lmasligi
        // mumkin, shuning uchun bloklash/biriktirish alohida ro'yxatdan olinadi.
        chargedTo: override?.chargeToLogin ?? stat?.chargedTo ?? null,
        blocked: override?.blocked ?? stat?.blocked ?? false,
      })
    }

    // Sarfi bor, lekin filtrlangan AD ro'yxatiga tushmagan loginlar — odatda
    // AD'da umuman topilmaganlar (unmatched). Faqat joriy filtrlarga mos
    // kelganlari qo'shiladi.
    for (const stat of stats.value) {
      const key = normalizeLogin(stat.login)
      if (seen.has(key)) continue
      if (!statRowPassesFilters(stat)) continue
      const override = overrideMap.get(key)
      result.push({
        login: stat.login,
        fullName: stat.fullName,
        department: stat.department,
        position: stat.position,
        used: stat.used,
        usedFromLinked: stat.usedFromLinked,
        usedTotal: stat.usedTotal,
        allocated: stat.allocated,
        remaining: stat.remaining,
        overLimit: stat.overLimit,
        matchStatus: stat.matchStatus,
        chargedTo: override?.chargeToLogin ?? stat.chargedTo,
        blocked: override?.blocked ?? stat.blocked,
      })
    }

    return result
  })

  const departmentOptions = computed(() => {
    const set = new Set<string>()
    for (const emp of directoryOptions.value) if (emp.department) set.add(emp.department)
    return Array.from(set).sort()
  })

  /**
   * Bloklash yoki biriktirishni saqlaydi.
   *
   * Saqlangandan keyin butun sahifa qayta yuklanadi: biriktirish sarf
   * raqamlarini ham o'zgartiradi (egasining "biriktirilganlardan" ustuni),
   * shuning uchun faqat mahalliy bayroqni yangilash yetarli emas.
   */
  async function saveOverride(login: string, body: UserOverrideInput) {
    await setUserOverride(login, body)
    await reload()
  }

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
    /** Biriktirish oynasida tanlash uchun — filtrlanmagan to'liq AD ro'yxati. */
    directoryOptions,
    defaultQuota,
    adSyncStatus,
    loading,
    error,
    saveQuota,
    saveOverride,
  }
}
