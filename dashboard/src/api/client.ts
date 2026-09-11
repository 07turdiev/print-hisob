import router from '../router'
import { useAuthStore } from '../stores/auth'
import type {
  AdSyncStatus,
  Agent,
  AgentQuery,
  AgentsSummary,
  DepartmentStat,
  Employee,
  EmployeeQuery,
  EmployeeQuota,
  EmployeeQuotaInput,
  EmployeeStat,
  FailureReason,
  LoginResponse,
  PeriodParams,
  PrintJobPage,
  PrintJobQuery,
  Printer,
  PrinterStat,
  StatsSummary,
  TimeseriesPoint,
  TopStats,
} from './types'

const BASE_URL = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type QueryValue = string | number | boolean | undefined | null

function toQueryString(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

interface RequestOptions {
  query?: Record<string, QueryValue>
  method?: string
  body?: unknown
  /** Set to false for endpoints that don't require the bearer token (login). */
  auth?: boolean
}

/** Performs the fetch, attaches the bearer token, and logs the user out on a 401. */
async function requestRaw(path: string, options: RequestOptions = {}): Promise<Response> {
  const { query, method = 'GET', body, auth = true } = options
  const url = `${BASE_URL}${path}${query ? toQueryString(query) : ''}`

  const headers: Record<string, string> = {}
  if (auth) {
    const token = useAuthStore().token
    if (token) headers['Authorization'] = `Bearer ${token}`
  }
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (auth && response.status === 401) {
    useAuthStore().logout()
    if (router.currentRoute.value.name !== 'login') {
      router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    }
  }

  return response
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await requestRaw(path, options)

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = data?.detail ? JSON.stringify(data.detail) : detail
    } catch {
      // response body is not JSON, keep statusText
    }
    throw new ApiError(response.status, `${options.method ?? 'GET'} ${path} -> ${response.status}: ${detail}`)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Converts the shared camelCase period params to the snake_case query keys the API expects. */
function periodQuery(params: PeriodParams): Record<string, QueryValue> {
  return {
    period_type: params.periodType,
    year: params.year,
    period_no: params.periodNo,
    department: params.department,
  }
}

// --- Auth --------------------------------------------------------------

export function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: { username, password },
    auth: false,
  })
}

// --- Stats ---------------------------------------------------------------

export function getSummary(params: PeriodParams): Promise<StatsSummary> {
  return request<StatsSummary>('/api/stats/summary', { query: periodQuery(params) })
}

export function getEmployeeStats(params: PeriodParams): Promise<EmployeeStat[]> {
  return request<EmployeeStat[]>('/api/stats/employees', { query: periodQuery(params) })
}

export function getTimeseries(params: PeriodParams): Promise<TimeseriesPoint[]> {
  return request<TimeseriesPoint[]>('/api/stats/timeseries', { query: periodQuery(params) })
}

export function getTopStats(params: PeriodParams, limit = 10): Promise<TopStats> {
  return request<TopStats>('/api/stats/top', { query: { ...periodQuery(params), limit } })
}

export function getFailures(params: PeriodParams): Promise<FailureReason[]> {
  return request<FailureReason[]>('/api/stats/failures', { query: periodQuery(params) })
}

export function getPrinterStats(params: PeriodParams): Promise<PrinterStat[]> {
  return request<PrinterStat[]>('/api/stats/printers', { query: periodQuery(params) })
}

// --- Printers registry (MAC-keyed) ---------------------------------------

export function getPrinters(q?: string): Promise<Printer[]> {
  return request<Printer[]>('/api/printers', { query: { q } })
}

/** Sets the friendly name for a printer. Empty string clears it (falls back to driver name). */
export function renamePrinter(mac: string, name: string): Promise<Printer> {
  return request<Printer>(`/api/printers/${encodeURIComponent(mac)}`, {
    method: 'PUT',
    body: { name },
  })
}

export function getDepartmentStats(params: PeriodParams): Promise<DepartmentStat[]> {
  return request<DepartmentStat[]>('/api/stats/departments', { query: periodQuery(params) })
}

/** Uzbek month names used only as a filename fallback if the server omits Content-Disposition. */
const UZ_MONTH_NAMES = [
  'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
  'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr',
]

function fallbackPeriodLabel(params: PeriodParams): string {
  return params.periodType === 'quarter'
    ? `${params.periodNo}-chorak`
    : UZ_MONTH_NAMES[params.periodNo - 1] ?? String(params.periodNo)
}

/** Extracts the filename from a `Content-Disposition` header, preferring the UTF-8 form. */
function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null
  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match) return decodeURIComponent(utf8Match[1])
  const plainMatch = header.match(/filename="?([^";]+)"?/i)
  return plainMatch ? plainMatch[1] : null
}

/**
 * Downloads the KPI CSV report (grouped by department, matches the quota table's period)
 * and saves it via a temporary `<a download>` link, since a plain `<a href>` can't send
 * the auth header. Reuses `requestRaw` so a 401 triggers the same logout redirect.
 */
export async function downloadEmployeesCsv(params: PeriodParams): Promise<void> {
  const response = await requestRaw('/api/stats/employees.csv', { query: periodQuery(params) })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = data?.detail ? JSON.stringify(data.detail) : detail
    } catch {
      // response body is not JSON on error
    }
    throw new ApiError(response.status, `GET /api/stats/employees.csv -> ${response.status}: ${detail}`)
  }

  const blob = await response.blob()
  const filename =
    filenameFromContentDisposition(response.headers.get('Content-Disposition')) ??
    `KPI qog'oz sarfi ${params.year} ${fallbackPeriodLabel(params)}.csv`

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

// --- Quotas --------------------------------------------------------------

export function getQuotas(
  params: Partial<PeriodParams> & { login?: string; department?: string },
): Promise<EmployeeQuota[]> {
  return request<EmployeeQuota[]>('/api/quotas', {
    query: {
      period_type: params.periodType,
      year: params.year,
      period_no: params.periodNo,
      login: params.login,
      department: params.department,
    },
  })
}

export function putQuotas(
  payload: EmployeeQuotaInput | EmployeeQuotaInput[],
): Promise<EmployeeQuota[]> {
  return request<EmployeeQuota[]>('/api/quotas', { method: 'PUT', body: payload })
}

// --- Employees (AD directory) --------------------------------------------

export function getEmployees(query: EmployeeQuery = {}): Promise<Employee[]> {
  return request<Employee[]>('/api/employees', {
    query: {
      department: query.department,
      is_active: query.isActive,
      q: query.q,
      limit: query.limit,
      offset: query.offset,
    },
  })
}

// --- Print jobs journal ------------------------------------------------------

/** Fetches a page of print jobs and reads the total row count from the X-Total-Count header. */
export async function getPrintJobs(query: PrintJobQuery = {}): Promise<PrintJobPage> {
  const response = await requestRaw('/api/print-jobs', {
    query: {
      computer: query.computer,
      user: query.user,
      printer: query.printer,
      printer_mac: query.printerMac,
      success: query.success,
      since: query.since,
      until: query.until,
      limit: query.limit,
      offset: query.offset,
    },
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = data?.detail ? JSON.stringify(data.detail) : detail
    } catch {
      // ignore non-JSON body
    }
    throw new ApiError(response.status, `GET /api/print-jobs -> ${response.status}: ${detail}`)
  }

  const jobs = (await response.json()) as PrintJobPage['jobs']
  const total = Number(response.headers.get('X-Total-Count') ?? jobs.length)
  return { jobs, total }
}

// --- Print agents (heartbeat monitor) ------------------------------------

export function getAgents(query: AgentQuery = {}): Promise<Agent[]> {
  return request<Agent[]>('/api/agents', {
    query: {
      working: query.working,
      stale: query.stale,
      q: query.q,
    },
  })
}

export function getAgentsSummary(): Promise<AgentsSummary> {
  return request<AgentsSummary>('/api/agents/summary')
}

// --- AD sync status --------------------------------------------------------

export function getAdSyncStatus(): Promise<AdSyncStatus> {
  return request<AdSyncStatus>('/api/ad-sync/status')
}
