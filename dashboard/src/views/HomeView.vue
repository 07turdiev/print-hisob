<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useHomeData } from '../composables/useHomeData'
import { formatRelativeMinutes } from '../utils/time'
import KpiCards from '../components/KpiCards.vue'
import TimeseriesChart from '../components/TimeseriesChart.vue'
import StatTile from '../components/StatTile.vue'
import AppIcon from '../components/AppIcon.vue'

const { summary, timeseries, overLimitCount, unmatchedCount, topDepartment, adSyncStatus, loading, error } =
  useHomeData()

const adSyncLabel = computed(() => {
  if (!adSyncStatus.value) return ''
  if (adSyncStatus.value.employeeCount === 0) return 'Xodimlar hali yuklanmagan'
  return `Oxirgi sinxron: ${formatRelativeMinutes(adSyncStatus.value.minutesSinceSync)}`
})

const periodLabel = computed(() => {
  if (!summary.value) return '—'
  return summary.value.periodType === 'quarter'
    ? `${summary.value.year}-yil, ${summary.value.periodNo}-chorak`
    : `${summary.value.year}-yil, ${summary.value.periodNo}-oy`
})

const numberFormat = new Intl.NumberFormat('uz-UZ')

const QUICK_LINKS = [
  {
    to: '/choraklik',
    icon: 'quarterly',
    label: 'Choraklik hisobot',
    desc: "Chorak bo'yicha xodimlar kesimi va kvota nazorati",
  },
  {
    to: '/oylik',
    icon: 'monthly',
    label: 'Oylik hisobot',
    desc: "Oy bo'yicha sarf dinamikasi va limitlar",
  },
  {
    to: '/xodimlar',
    icon: 'employees',
    label: 'Xodimlar va kvotalar',
    desc: 'Kvotalarni belgilash va AD sinxron holati',
  },
  {
    to: '/jurnal',
    icon: 'journal',
    label: 'Chop etishlar jurnali',
    desc: "Har bir chop etish hodisasi bo'yicha batafsil ma'lumot",
  },
]
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
    </p>

    <div class="period-strip">
      <AppIcon name="monthly" :size="15" />
      <span>Joriy hisobot davri:</span>
      <strong>{{ periodLabel }}</strong>
      <span v-if="summary" class="period-strip__extra">
        · Standart kvota: {{ numberFormat.format(summary.defaultQuota) }} varaq
      </span>
    </div>

    <KpiCards :summary="summary" />

    <div class="grid-3">
      <StatTile
        label="Limitdan oshgan xodimlar"
        :value="overLimitCount"
        icon="warning"
        :tone="overLimitCount > 0 ? 'danger' : 'success'"
        :hint="overLimitCount > 0 ? 'Kvotasi tugagan xodimlar' : 'Barchasi kvota ichida'"
        to="/xodimlar"
      />
      <StatTile
        label="Noma'lum foydalanuvchilar"
        :value="unmatchedCount"
        icon="user"
        :tone="unmatchedCount > 0 ? 'warning' : 'success'"
        :hint="unmatchedCount > 0 ? 'AD ro\'yxatida topilmadi' : 'Barcha loginlar AD bilan mos'"
        to="/jurnal"
      />
      <StatTile
        label="Eng ko'p chop etgan bo'lim"
        :value="topDepartment?.name ?? '—'"
        icon="departments"
        tone="accent"
        :hint="topDepartment ? `${numberFormat.format(topDepartment.pages)} varaq` : undefined"
        to="/bolimlar"
      />
      <StatTile
        v-if="adSyncStatus?.isStale"
        label="AD sinxronizatsiyasi"
        value="Eskirgan"
        icon="refresh"
        tone="warning"
        :hint="adSyncLabel"
        to="/xodimlar"
      />
    </div>

    <TimeseriesChart :points="timeseries" />

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="layers" :size="16" /></span>
          Tezkor o'tish
        </h2>
      </header>
      <div class="quick-list">
        <RouterLink v-for="link in QUICK_LINKS" :key="link.to" :to="link.to" class="quick-item">
          <span class="quick-item__icon"><AppIcon :name="link.icon" :size="17" /></span>
          <span class="quick-item__text">
            <span class="quick-item__label">{{ link.label }}</span>
            <span class="quick-item__desc">{{ link.desc }}</span>
          </span>
          <AppIcon name="arrow-right" :size="15" class="quick-item__arrow" />
        </RouterLink>
      </div>
    </section>

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
/* Joriy davrni eslatuvchi ingichka lenta */
.period-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 7px var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-accent);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.period-strip strong {
  color: var(--color-text);
}

.period-strip__extra {
  color: var(--color-text-muted);
}

.quick-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.quick-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px var(--space-4);
  border-right: 1px solid var(--color-border);
  border-top: 1px solid var(--color-border);
  color: var(--color-text);
  text-decoration: none;
  transition: background-color var(--transition);
}

.quick-item:first-child {
  border-top: none;
}

.quick-item:hover {
  background: var(--color-accent-soft-bg);
  text-decoration: none;
}

.quick-item__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
}

.quick-item__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.quick-item__label {
  font-size: var(--font-size-base);
  font-weight: 600;
}

.quick-item__desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-item__arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.quick-item:hover .quick-item__arrow {
  color: var(--color-accent);
}

/* Oxirgi ustundagi ajratuvchi chiziq keraksiz */
@media (min-width: 1100px) {
  .quick-item:last-child {
    border-right: none;
  }

  .quick-item {
    border-top: none;
  }
}
</style>
