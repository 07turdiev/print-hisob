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
  /** Default quota (in pages) applied to employees with no explicit quota row for this period. */
  defaultQuota: number
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
  /** Stable identity; `null` for legacy printers grouped by driver name (no MAC reported). */
  mac: string | null
  /** Resolved display name: admin custom name -> last driver name -> raw event name -> mac. */
  name: string
  pages: number
  jobs: number
  successRate: number
  failedJobs: number
  lastIp: string | null
}

/** One row from GET/PUT /api/printers — the MAC-keyed printer registry. */
export interface Printer {
  mac: string
  /** Admin-set friendly name; `null` when not set (falls back to driver name / mac for display). */
  name: string | null
  /** Ready-to-show name: `name` -> `lastDriverName` -> `mac`. */
  displayName: string
  lastIp: string | null
  lastDriverName: string | null
  lastSeen: string | null
  firstSeen: string
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
  /** Raw driver name as reported by that workstation — differs per PC for the same device. */
  printer: string
  /** Ready-to-show name resolved from the MAC-keyed registry:
   *  admin name -> last driver name -> raw name. Use this for display, not `printer`. */
  printerName: string | null
  printerIp: string | null
  /** Sheet count for this job (accounts for duplex; field name kept as `pages` for API stability). */
  pages: number
  /** Document page count (fayldagi sahifa soni) — informational only, does not affect `pages`/consumption. */
  documentPages: number
  /** Whether the job printed double-sided. */
  duplex: boolean
  timestamp: string
  success: boolean
  reason: string | null
  /** Stable printer identity; `null` when the agent didn't report a MAC. */
  printerMac: string | null
  /** Spooler job id, informational only; `null` when not reported. */
  jobId: string | null
}

export interface PrintJobQuery {
  computer?: string
  user?: string
  /** Partial match against both the registry name and the raw driver name. */
  printer?: string
  /** Exact device filter by MAC address. */
  printerMac?: string
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
  /** Person's display name (not a login) as reported by the agent.
   *  Null when nobody is signed in (lock/login screen) — the agent sends "". */
  username: string | null
  /** Agent version; null for agents that don't report it. */
  version: string | null
  working: boolean
  /** Error/status message from the agent; null when everything is fine. */
  detail: string | null
  /** Workstation boot time (UTC, ISO); null for older agents that don't report it. */
  bootTimeUtc: string | null
  /** Workstation uptime in seconds since boot; null for older agents. */
  uptimeSeconds: number | null
  /** How long the agent process itself has been running, in seconds; null for older agents. */
  agentUptimeSeconds: number | null
  reportedAt: string
  /** Hasn't reported within the server-configured stale window; treat as offline. */
  isStale: boolean
  minutesSinceReport: number
  /** Server-computed: agent process started very recently — may indicate a crash loop. */
  recentlyRestarted: boolean
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
  recentlyRestarted: number
}

// --- AD sync status ---------------------------------------------------------

/** GET /api/ad-sync/status — health of the hourly Active Directory employee sync. */
export interface AdSyncStatus {
  /** ISO timestamp of the last successful sync; null when there are no employees yet. */
  lastSyncedAt: string | null
  employeeCount: number
  activeCount: number
  /** null when there are no employees yet. */
  minutesSinceSync: number | null
  /** True when the last sync is older than the server threshold, or there are zero employees. */
  isStale: boolean
}
