<script setup lang="ts">
import { useAgentsPage } from '../composables/useAgentsPage'
import type { Agent } from '../api/types'
import AppIcon from '../components/AppIcon.vue'

const { search, onlyErrors, onlyStale, agents, summary, loading, error, sortKey, sortDesc, setSort } =
  useAgentsPage()

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
              </td>
              <td class="detail-cell">{{ agent.detail ?? '—' }}</td>
              <td class="nowrap" :title="formatTimestamp(agent.reportedAt)">
                {{ formatRelative(agent.minutesSinceReport) }}
              </td>
            </tr>
            <tr v-if="!agents.length">
              <td colspan="6" class="empty">Hozircha hech qaysi agentdan signal kelmagan.</td>
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
