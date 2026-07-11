import { computed, ref, watch } from 'vue'
import { ApiError, getEmployees, getPrintJobs } from '../api/client'
import type { Employee, MatchStatus, PrintJob } from '../api/types'

export type SuccessFilter = '' | 'true' | 'false'

/** Drives the Chop etishlar jurnali page: filterable, paginated /api/print-jobs listing. */
export function useJournalPage() {
  const computer = ref('')
  const user = ref('')
  const printer = ref('')
  const success = ref<SuccessFilter>('')
  const since = ref('')
  const until = ref('')

  const page = ref(1)
  const pageSize = ref(25)

  const jobs = ref<PrintJob[]>([])
  const total = ref(0)
  const employees = ref<Employee[]>([])

  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadEmployees() {
    try {
      employees.value = await getEmployees({ limit: 1000 })
    } catch {
      // Non-critical: match-status badges just fall back to "unmatched" if this fails.
    }
  }

  async function reload() {
    loading.value = true
    error.value = null
    try {
      const res = await getPrintJobs({
        computer: computer.value || undefined,
        user: user.value || undefined,
        printer: printer.value || undefined,
        success: success.value === '' ? undefined : success.value === 'true',
        since: since.value || undefined,
        until: until.value || undefined,
        limit: pageSize.value,
        offset: (page.value - 1) * pageSize.value,
      })
      jobs.value = res.jobs
      total.value = res.total
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  let filterTimer: ReturnType<typeof setTimeout> | undefined
  watch([computer, user, printer, success, since, until], () => {
    page.value = 1
    clearTimeout(filterTimer)
    filterTimer = setTimeout(reload, 300)
  })
  watch(page, reload)

  reload()
  loadEmployees()

  const activeLogins = computed(() => new Set(employees.value.filter((e) => e.isActive).map((e) => e.login)))
  const inactiveLogins = computed(() => new Set(employees.value.filter((e) => !e.isActive).map((e) => e.login)))

  function matchStatusFor(login: string): MatchStatus {
    if (activeLogins.value.has(login)) return 'active'
    if (inactiveLogins.value.has(login)) return 'inactive'
    return 'unmatched'
  }

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  function nextPage() {
    if (page.value < totalPages.value) page.value++
  }
  function prevPage() {
    if (page.value > 1) page.value--
  }

  return {
    computer,
    user,
    printer,
    success,
    since,
    until,
    page,
    pageSize,
    totalPages,
    jobs,
    total,
    loading,
    error,
    matchStatusFor,
    nextPage,
    prevPage,
    reload,
  }
}
