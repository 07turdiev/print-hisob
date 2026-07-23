<script setup lang="ts">
import { useAgentsPage } from '../composables/useAgentsPage'
import type { Agent } from '../api/types'
import AppIcon from '../components/AppIcon.vue'

const {
  search,
  onlyErrors,
  onlyStale,
  onlyRecentlyRestarted,
  agents,
  summary,
  loading,
  error,
  sortKey,
  sortDesc,
  setSort,
} = useAgentsPage()

const numberFormat = new Intl.NumberFormat('uz-UZ')
const dateTimeFormat = new Intl.DateTimeFormat('uz-UZ', { dateStyle: 'medium', timeStyle: 'short' })

function fmt(value: number | undefined): string {
  return value === undefined ? '-' : numberFormat.format(value)
}

function formatTimestamp(iso: string): string {
  try {
    return dateTimeFormat.format(new Date(iso))
  } catch {
    return iso
  }
}

/** Human-friendly relative time in Uzbek; the workstation clock could rarely put this at/below zero. */
function formatRelative(minutes: number): string {
  if (minutes <= 0) return 'hozir'
  if (minutes < 60) return `${minutes} daqiqa oldin`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} soat oldin`
  const days = Math.floor(hours / 24)
  return `${days} kun oldin`
}

/** Formats a duration in seconds as a short human-readable Uzbek string, e.g. "3 soat 20 daqiqa". */
function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 60) return `${Math.floor(seconds)} soniya`

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} daqiqa`

  const hours = Math.floor(minutes / 60)
  const remMinutes = minutes % 60
  if (hours < 24) {
    return remMinutes > 0 ? `${hours} soat ${remMinutes} daqiqa` : `${hours} soat`
  }

  const days = Math.floor(hours / 24)
  const remHours = hours % 24
  return remHours > 0 ? `${days} kun ${remHours} soat` : `${days} kun`
}

function bootTimeTitle(agent: Agent): string {
  if (!agent.bootTimeUtc) return ''
  return `Yoqilgan: ${formatTimestamp(agent.bootTimeUtc)}`
}

type StatusKind = 'ok' | 'error' | 'stale'

/** Stale (no heartbeat) takes precedence over the raw `working` flag in the badge shown. */
function statusKind(agent: Agent): StatusKind {
  if (agent.isStale) return 'stale'
  if (!agent.working) return 'error'
  return 'ok'
}

const STATUS_LABEL: Record<StatusKind, string> = {
  ok: 'Ishlayapti',
  error: 'Xato',
  stale: "Aloqa yo'q",
}

function sortIndicator(key: string): string {
  if (sortKey.value !== key) return ''
  return sortDesc.value ? ' ▼' : ' ▲'
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>

    <div class="kpi-grid">
      <div class="card kpi">
        <span class="kpi-label">Jami agentlar</span>
        <span class="kpi-value">{{ fmt(summary?.total) }}</span>
      </div>
      <div class="card kpi">
        <span class="kpi-label">Ishlayapti</span>
        <span class="kpi-value kpi-ok">{{ fmt(summary?.working) }}</span>
      </div>
      <div class="card kpi" :class="{ 'kpi-alert': (summary?.notWorking ?? 0) > 0 }">
        <span class="kpi-label">Xato</span>
        <span class="kpi-value" :class="{ 'kpi-danger': (summary?.notWorking ?? 0) > 0 }">
          {{ fmt(summary?.notWorking) }}
        </span>
      </div>
      <div class="card kpi" :class="{ 'kpi-alert': (summary?.stale ?? 0) > 0 }">
        <span class="kpi-label">Aloqa yo'q</span>
        <span class="kpi-value" :class="{ 'kpi-warning': (summary?.stale ?? 0) > 0 }">
          {{ fmt(summary?.stale) }}
        </span>
      </div>
      <div class="card kpi" :class="{ 'kpi-alert': (summary?.recentlyRestarted ?? 0) > 0 }">
        <span class="kpi-label">Yaqinda qayta ishga tushgan</span>
        <span class="kpi-value" :class="{ 'kpi-warning': (summary?.recentlyRestarted ?? 0) > 0 }">
          {{ fmt(summary?.recentlyRestarted) }}
        </span>
      </div>
    </div>

    <div class="filters card">
      <label class="search-box">
        <AppIcon name="search" :size="16" />
        <input v-model="search" type="text" placeholder="Kompyuter yoki foydalanuvchi bo'yicha qidirish" />
      </label>

      <label class="toggle">
        <input v-model="onlyErrors" type="checkbox" />
        <span>Faqat xatolar</span>
      </label>

      <label class="toggle">
        <input v-model="onlyStale" type="checkbox" />
        <span>Faqat aloqa yo'q</span>
      </label>

      <label class="toggle">
        <input v-model="onlyRecentlyRestarted" type="checkbox" />
        <span>Faqat qayta ishga tushganlar</span>
      </label>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="sortable" @click="setSort('computer')">Kompyuter{{ sortIndicator('computer') }}</th>
              <th class="sortable" @click="setSort('username')">Foydalanuvchi{{ sortIndicator('username') }}</th>
              <th class="sortable" @click="setSort('version')">Versiya{{ sortIndicator('version') }}</th>
              <th class="sortable" @click="setSort('status')">Holat{{ sortIndicator('status') }}</th>
              <th class="sortable" @click="setSort('detail')">Tafsilot{{ sortIndicator('detail') }}</th>
              <th class="sortable" @click="setSort('reportedAt')">Oxirgi signal{{ sortIndicator('reportedAt') }}</th>
              <th class="sortable" @click="setSort('uptimeSeconds')">
                Kompyuter ishlagan{{ sortIndicator('uptimeSeconds') }}
              </th>
              <th class="sortable" @click="setSort('agentUptimeSeconds')">
                Agent ishlagan{{ sortIndicator('agentUptimeSeconds') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="agent in agents"
              :key="agent.computer"
              :class="{ 'row-error': statusKind(agent) === 'error', 'row-stale': statusKind(agent) === 'stale' }"
            >
              <td>{{ agent.computer }}</td>
              <td>{{ agent.username }}</td>
              <td>{{ agent.version }}</td>
              <td>
                <span class="badge" :class="`badge--${statusKind(agent)}`">{{ STATUS_LABEL[statusKind(agent)] }}</span>
                <span v-if="agent.recentlyRestarted" class="badge badge--restarted" title="Agent yaqinda qayta ishga tushgan">
                  ⟳ qayta ishga tushgan
                </span>
              </td>
              <td class="detail-cell">{{ agent.detail ?? '—' }}</td>
              <td class="nowrap" :title="formatTimestamp(agent.reportedAt)">
                {{ formatRelative(agent.minutesSinceReport) }}
              </td>
              <td class="nowrap" :title="bootTimeTitle(agent)">
                {{ formatDuration(agent.uptimeSeconds) }}
              </td>
              <td
                class="nowrap"
                :class="{ 'cell-restarted': agent.recentlyRestarted }"
                :title="
                  agent.recentlyRestarted
                    ? 'Agent yaqinda qayta ishga tushgan — takrorlansa, agent qulab tushayotgan bo\'lishi mumkin'
                    : undefined
                "
              >
                {{ formatDuration(agent.agentUptimeSeconds) }}
              </td>
            </tr>
            <tr v-if="!agents.length">
              <td colspan="8" class="empty">Hozircha hech qaysi agentdan signal kelmagan.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p v-if="loading" class="loading-hint">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-width: 1280px;
  margin: 0 auto;
  padding: 1.5rem;
}

.error-banner {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  padding: 0.6rem 1rem;
  border-radius: 8px;
  margin: 0;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.kpi {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.kpi-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.kpi-value {
  font-size: 1.8rem;
  font-weight: 700;
}

.kpi-ok {
  color: var(--color-success-fg);
}

.kpi-danger {
  color: var(--color-danger-fg);
}

.kpi-warning {
  color: var(--color-warning-fg);
}

.kpi-alert {
  border-color: var(--color-warning-fg);
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  align-items: center;
  padding: 0.85rem 1.25rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  color: var(--color-text-muted);
  min-width: 18rem;
  flex: 1;
}

.search-box input {
  border: none;
  background: transparent;
  color: var(--color-text);
  flex: 1;
  font-size: 0.9rem;
}

.search-box input:focus {
  outline: none;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.table-wrap {
  overflow-x: auto;
}

th.sortable {
  cursor: pointer;
}

.nowrap {
  white-space: nowrap;
}

.detail-cell {
  max-width: 18rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-error {
  background: var(--color-danger-bg);
}

.row-stale {
  background: var(--color-muted-bg);
}

.badge {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.badge--ok {
  background: var(--color-success-bg);
  color: var(--color-success-fg);
}

.badge--error {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
}

.badge--stale {
  background: var(--color-muted-bg);
  color: var(--color-muted-fg);
}

.badge--restarted {
  background: var(--color-warning-bg);
  color: var(--color-warning-fg);
  margin-left: 0.4rem;
}

.cell-restarted {
  background: var(--color-warning-bg);
  color: var(--color-warning-fg);
  border-radius: 4px;
}

.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: 1.5rem;
}

.loading-hint {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
</style>
