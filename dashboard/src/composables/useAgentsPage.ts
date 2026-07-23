import { computed, onUnmounted, ref, watch } from 'vue'
import { ApiError, getAgents, getAgentsSummary } from '../api/client'
import type { Agent, AgentsSummary } from '../api/types'

const AUTO_REFRESH_MS = 60_000

export type SortKey =
  | 'computer'
  | 'username'
  | 'version'
  | 'status'
  | 'detail'
  | 'reportedAt'
  | 'uptimeSeconds'
  | 'agentUptimeSeconds'

/**
 * Higher score = bigger problem, so the default "problem rows first" sort surfaces them.
 * A recently-restarted agent ranks above healthy ones but below actual errors/offline.
 */
function problemScore(agent: Agent): number {
  if (agent.isStale) return 3
  if (!agent.working) return 2
  if (agent.recentlyRestarted) return 1
  return 0
}

/** Ascending numeric compare treating null as "last" regardless of sort direction. */
function compareNullableNumber(a: number | null, b: number | null, dir: 1 | -1): number {
  if (a === null && b === null) return 0
  if (a === null) return 1
  if (b === null) return -1
  return dir * (a - b)
}

/** Drives the Agentlar page: polls the print-agent heartbeat list and its summary counters. */
export function useAgentsPage() {
  const search = ref('')
  const onlyErrors = ref(false)
  const onlyStale = ref(false)
  /** Client-side only filter — the backend has no `recentlyRestarted` query param. */
  const onlyRecentlyRestarted = ref(false)

  const agents = ref<Agent[]>([])
  const summary = ref<AgentsSummary | null>(null)

  const loading = ref(false)
  const error = ref<string | null>(null)

  const sortKey = ref<SortKey>('status')
  const sortDesc = ref(true)

  function setSort(key: SortKey) {
    if (sortKey.value === key) {
      sortDesc.value = !sortDesc.value
    } else {
      sortKey.value = key
      // Numeric problem-based columns read more naturally starting descending; text columns ascending.
      sortDesc.value = key === 'status' || key === 'reportedAt'
    }
  }

  async function reload() {
    loading.value = true
    error.value = null
    try {
      const [agentsRes, summaryRes] = await Promise.all([
        getAgents({
          q: search.value || undefined,
          working: onlyErrors.value ? false : undefined,
          stale: onlyStale.value ? true : undefined,
        }),
        getAgentsSummary(),
      ])
      agents.value = agentsRes
      summary.value = summaryRes
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  let searchTimer: ReturnType<typeof setTimeout> | undefined
  watch(search, () => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(reload, 300)
  })
  watch([onlyErrors, onlyStale], reload)

  reload()

  const refreshTimer = setInterval(reload, AUTO_REFRESH_MS)
  onUnmounted(() => {
    clearTimeout(searchTimer)
    clearInterval(refreshTimer)
  })

  const sortedAgents = computed(() => {
    const dir = sortDesc.value ? -1 : 1
    const list = onlyRecentlyRestarted.value
      ? agents.value.filter((agent) => agent.recentlyRestarted)
      : [...agents.value]
    list.sort((a, b) => {
      switch (sortKey.value) {
        case 'computer':
          return dir * a.computer.localeCompare(b.computer)
        case 'username':
          return dir * a.username.localeCompare(b.username)
        case 'version':
          return dir * a.version.localeCompare(b.version)
        case 'detail':
          return dir * (a.detail ?? '').localeCompare(b.detail ?? '')
        case 'reportedAt':
          return dir * (a.minutesSinceReport - b.minutesSinceReport)
        case 'uptimeSeconds':
          return compareNullableNumber(a.uptimeSeconds, b.uptimeSeconds, dir as 1 | -1)
        case 'agentUptimeSeconds':
          return compareNullableNumber(a.agentUptimeSeconds, b.agentUptimeSeconds, dir as 1 | -1)
        case 'status':
        default: {
          const diff = problemScore(a) - problemScore(b)
          return diff !== 0 ? dir * diff : a.computer.localeCompare(b.computer)
        }
      }
    })
    return list
  })

  return {
    search,
    onlyErrors,
    onlyStale,
    onlyRecentlyRestarted,
    agents: sortedAgents,
    summary,
    loading,
    error,
    sortKey,
    sortDesc,
    setSort,
    reload,
  }
}
