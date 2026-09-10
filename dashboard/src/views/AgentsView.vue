<script setup lang="ts">
import { computed } from 'vue'
import { useAgentsPage } from '../composables/useAgentsPage'
import type { Agent } from '../api/types'
import AppIcon from '../components/AppIcon.vue'
import StatTile from '../components/StatTile.vue'

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
  return value === undefined ? '—' : numberFormat.format(value)
}

function formatTimestamp(iso: string): string {
  try {
    return dateTimeFormat.format(new Date(iso))
  } catch {
    return iso
  }
}

/** O'zbekcha nisbiy vaqt; ish stantsiyasi soati kamdan-kam holda nolga teng bo'lishi mumkin. */
function formatRelative(minutes: number): string {
  if (minutes <= 0) return 'hozir'
  if (minutes < 60) return `${minutes} daqiqa oldin`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} soat oldin`
  const days = Math.floor(hours / 24)
  return `${days} kun oldin`
}

/** Soniyalarni qisqa o'zbekcha davomiylikka aylantiradi, masalan "3 soat 20 daqiqa". */
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

/** Aloqa yo'qligi (stale) `working` bayrog'idan ustun turadi. */
function statusKind(agent: Agent): StatusKind {
  if (agent.isStale) return 'stale'
  if (!agent.working) return 'error'
  return 'ok'
}

const STATUS_META: Record<StatusKind, { label: string; tone: string }> = {
  ok: { label: 'Ishlayapti', tone: 'success' },
  error: { label: 'Xato', tone: 'danger' },
  stale: { label: "Aloqa yo'q", tone: 'muted' },
}

function sortCaret(key: string): string {
  if (sortKey.value !== key) return ''
  return sortDesc.value ? '▼' : '▲'
}

const hasFilters = computed(
  () => Boolean(search.value) || onlyErrors.value || onlyStale.value || onlyRecentlyRestarted.value,
)

function clearFilters() {
  search.value = ''
  onlyErrors.value = false
  onlyStale.value = false
  onlyRecentlyRestarted.value = false
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
    </p>

    <div class="grid-3">
      <StatTile label="Jami agentlar" :value="fmt(summary?.total)" icon="agents" tone="muted" hint="Ro'yxatga olingan ish stantsiyalari" />
      <StatTile label="Ishlayapti" :value="fmt(summary?.working)" icon="check-circle" tone="success" />
      <StatTile
        label="Xato"
        :value="fmt(summary?.notWorking)"
        icon="warning"
        :tone="(summary?.notWorking ?? 0) > 0 ? 'danger' : 'muted'"
      />
      <StatTile
        label="Aloqa yo'q"
        :value="fmt(summary?.stale)"
        icon="clock"
        :tone="(summary?.stale ?? 0) > 0 ? 'warning' : 'muted'"
      />
      <StatTile
        label="Yaqinda qayta ishga tushgan"
        :value="fmt(summary?.recentlyRestarted)"
        icon="refresh"
        :tone="(summary?.recentlyRestarted ?? 0) > 0 ? 'warning' : 'muted'"
        hint="Takrorlansa — agent qulab tushayotgan bo'lishi mumkin"
      />
    </div>

    <div class="filter-bar">
      <label class="field field--grow">
        <span>Qidiruv</span>
        <span class="search-box">
          <AppIcon name="search" :size="15" />
          <input v-model="search" type="text" placeholder="Kompyuter yoki foydalanuvchi bo'yicha qidirish" />
        </span>
      </label>

      <div class="field">
        <span class="field-label">Filtrlar</span>
        <div class="checks">
          <label class="check"><input v-model="onlyErrors" type="checkbox" /> Faqat xatolar</label>
          <label class="check"><input v-model="onlyStale" type="checkbox" /> Faqat aloqa yo'q</label>
          <label class="check">
            <input v-model="onlyRecentlyRestarted" type="checkbox" /> Faqat qayta ishga tushganlar
          </label>
        </div>
      </div>

      <button type="button" class="btn clear-btn" :disabled="!hasFilters" @click="clearFilters">
        <AppIcon name="close" :size="14" />
        Tozalash
      </button>
    </div>

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="agents" :size="16" /></span>
          Agentlar ro'yxati
        </h2>
        <span class="panel__count">{{ agents.length }} ta yozuv</span>
      </header>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-num">T/r</th>
              <th class="sortable" @click="setSort('computer')">
                Kompyuter <span class="sort-caret">{{ sortCaret('computer') }}</span>
              </th>
              <th class="sortable" @click="setSort('username')">
                Foydalanuvchi <span class="sort-caret">{{ sortCaret('username') }}</span>
              </th>
              <th class="sortable" @click="setSort('version')">
                Versiya <span class="sort-caret">{{ sortCaret('version') }}</span>
              </th>
              <th class="sortable" @click="setSort('status')">
                Holat <span class="sort-caret">{{ sortCaret('status') }}</span>
              </th>
              <th class="sortable" @click="setSort('detail')">
                Tafsilot <span class="sort-caret">{{ sortCaret('detail') }}</span>
              </th>
              <th class="sortable" @click="setSort('reportedAt')">
                Oxirgi signal <span class="sort-caret">{{ sortCaret('reportedAt') }}</span>
              </th>
              <th class="sortable" @click="setSort('uptimeSeconds')">
                Kompyuter ishlagan <span class="sort-caret">{{ sortCaret('uptimeSeconds') }}</span>
              </th>
              <th class="sortable" @click="setSort('agentUptimeSeconds')">
                Agent ishlagan <span class="sort-caret">{{ sortCaret('agentUptimeSeconds') }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(agent, i) in agents"
              :key="agent.computer"
              :class="{
                'row-danger': statusKind(agent) === 'error',
                'row-muted': statusKind(agent) === 'stale',
              }"
            >
              <td class="col-num">{{ i + 1 }}</td>
              <td class="strong nowrap">{{ agent.computer }}</td>
              <td class="nowrap">{{ agent.username }}</td>
              <td class="nowrap muted">{{ agent.version }}</td>
              <td>
                <div class="status-cell">
                  <span class="badge" :class="`badge--${STATUS_META[statusKind(agent)].tone}`">
                    {{ STATUS_META[statusKind(agent)].label }}
                  </span>
                  <span
                    v-if="agent.recentlyRestarted"
                    class="badge badge--warning badge--plain"
                    title="Agent yaqinda qayta ishga tushgan"
                  >
                    <AppIcon name="refresh" :size="11" /> qayta ishga tushgan
                  </span>
                </div>
              </td>
              <td class="detail-cell" :title="agent.detail ?? ''">{{ agent.detail ?? '—' }}</td>
              <td class="nowrap" :title="formatTimestamp(agent.reportedAt)">
                {{ formatRelative(agent.minutesSinceReport) }}
              </td>
              <td class="nowrap muted" :title="bootTimeTitle(agent)">
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
              <td colspan="9" class="empty">Hozircha hech qaysi agentdan signal kelmagan.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.checks {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  height: 32px;
}

.clear-btn {
  margin-left: auto;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.detail-cell {
  max-width: 18rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-restarted {
  color: var(--color-warning-fg);
  font-weight: 600;
}
</style>
