// Types mirror the FastAPI response models in `api/app/schemas.py` exactly
// (camelCase JSON keys via `serialization_alias` / `alias` on the backend).

export type PeriodType = 'month' | 'quarter'

export type MatchStatus = 'active' | 'inactive' | 'unmatched'

/** Common query params accepted by every /api/stats/* endpoint. */
export interface PeriodParams {
  periodType: PeriodType
  year: number
  periodNo: number
  /** Optional server-side rollup filter, supported by every /api/stats/* endpoint. */
  department?: string
}

export interface StatsSummary {
  periodType: string
  year: number
  periodNo: number
  totalPages: number
  totalJobs: number
  successRate: number
  activePrinters: number
}

export interface EmployeeStat {
  login: string
  fullName: string | null
  department: string | null
  position: string | null
  used: number
  allocated: number
  remaining: number
  overLimit: boolean
  matchStatus: MatchStatus
}

export interface TimeseriesPoint {
  date: string
  pages: number
  jobs: number
}

export interface TopItem {
  name: string
  pages: number
  jobs: number
}

export interface TopStats {
  printers: TopItem[]
  computers: TopItem[]
  departments: TopItem[]
}

export interface FailureReason {
  reason: string
  count: number
}

export interface EmployeeQuota {
  login: string
  periodType: string
  year: number
  periodNo: number
  allocatedPages: number
}

/** Body for PUT /api/quotas (camelCase, matches EmployeeQuotaIn aliases). */
export interface EmployeeQuotaInput {
  login: string
  periodType: PeriodType
  year: number
  periodNo: number
  allocatedPages: number
}

// --- Auth ---------------------------------------------------------------

export interface LoginResponse {
  accessToken: string
  tokenType: string
  /** Token lifetime in seconds. */
  expiresIn: number
}

// --- Employees (AD directory) --------------------------------------------

/** One row from GET /api/employees — the full AD directory, synced hourly server-side. */
export interface Employee {
  login: string
  fullName: string | null
  department: string | null
  position: string | null
  isActive: boolean
  syncedAt: string
}

export interface EmployeeQuery {
  department?: string
  isActive?: boolean
  q?: string
  limit?: number
  offset?: number
}

/** A row combining the AD directory with the current period's usage/quota, used on the Xodimlar page. */
export interface MergedEmployeeRow {
  login: string
  fullName: string | null
  department: string | null
  position: string | null
  used: number
  allocated: number
  remaining: number
  overLimit: boolean
  matchStatus: MatchStatus
}

// --- Printers --------------------------------------------------------------

export interface PrinterStat {
  name: string
  pages: number
  jobs: number
  successRate: number
  failedJobs: number
}

// --- Departments ---------------------------------------------------------

export interface DepartmentStat {
  name: string
  pages: number
  jobs: number
  employeeCount: number
  totalAllocated: number
  remaining: number
  overLimit: boolean
}

// --- Print jobs journal ------------------------------------------------------

export interface PrintJob {
  id: number
  computer: string
  user: string
  document: string
  printer: string
  printerIp: string
  /** Sheet count for this job (accounts for duplex; field name kept as `pages` for API stability). */
  pages: number
  /** Document page count (fayldagi sahifa soni) — informational only, does not affect `pages`/consumption. */
  documentPages: number
  /** Whether the job printed double-sided. */
  duplex: boolean
  timestamp: string
  success: boolean
  reason: string | null
}

export interface PrintJobQuery {
  computer?: string
  user?: string
  printer?: string
  success?: boolean
  since?: string
  until?: string
  limit?: number
  offset?: number
}

export interface PrintJobPage {
  jobs: PrintJob[]
  total: number
}

// --- Print agents (heartbeat monitor) ------------------------------------

/** One row from GET /api/agents — the last reported heartbeat of a workstation's print agent. */
export interface Agent {
  computer: string
  /** Person's display name (not a login) as reported by the agent. */
  username: string
  version: string
  working: boolean
  /** Error/status message from the agent; null when everything is fine. */
  detail: string | null
  reportedAt: string
  /** Hasn't reported within the server-configured stale window; treat as offline. */
  isStale: boolean
  minutesSinceReport: number
}

export interface AgentQuery {
  working?: boolean
  stale?: boolean
  q?: string
}

export interface AgentsSummary {
  total: number
  working: number
  notWorking: number
  stale: number
}
