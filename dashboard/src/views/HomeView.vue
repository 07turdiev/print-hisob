<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useHomeData } from '../composables/useHomeData'
import KpiCards from '../components/KpiCards.vue'
import TimeseriesChart from '../components/TimeseriesChart.vue'
import AppIcon from '../components/AppIcon.vue'

const { summary, timeseries, overLimitCount, unmatchedCount, topDepartment, loading, error } = useHomeData()

const periodLabel = computed(() => {
  if (!summary.value) return ''
  return summary.value.periodType === 'quarter'
    ? `${summary.value.year}, ${summary.value.periodNo}-chorak`
    : `${summary.value.year}-yil, ${summary.value.periodNo}-oy`
})
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>
    <p class="period-hint">Joriy davr: <strong>{{ periodLabel }}</strong></p>

    <KpiCards :summary="summary" />

    <div class="highlight-grid">
      <RouterLink to="/xodimlar" class="card highlight" :class="{ danger: overLimitCount > 0 }">
        <AppIcon name="warning" :size="22" />
        <div>
          <div class="highlight-value">{{ overLimitCount }}</div>
          <div class="highlight-label">Limitdan oshgan xodimlar</div>
        </div>
      </RouterLink>

      <RouterLink to="/jurnal" class="card highlight" :class="{ warn: unmatchedCount > 0 }">
        <AppIcon name="user" :size="22" />
        <div>
          <div class="highlight-value">{{ unmatchedCount }}</div>
          <div class="highlight-label">Noma'lum foydalanuvchilar</div>
        </div>
      </RouterLink>

      <RouterLink to="/bolimlar" class="card highlight">
        <AppIcon name="departments" :size="22" />
        <div>
          <div class="highlight-value">{{ topDepartment?.name ?? '-' }}</div>
          <div class="highlight-label">Eng ko'p chop etgan bo'lim</div>
        </div>
      </RouterLink>
    </div>

    <TimeseriesChart :points="timeseries" />

    <div class="quick-links">
      <RouterLink to="/choraklik" class="card link-card">Choraklik hisobot &rarr;</RouterLink>
      <RouterLink to="/oylik" class="card link-card">Oylik hisobot &rarr;</RouterLink>
      <RouterLink to="/xodimlar" class="card link-card">Xodimlar va kvotalar &rarr;</RouterLink>
      <RouterLink to="/printerlar" class="card link-card">Printerlar &rarr;</RouterLink>
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

.period-hint {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.error-banner {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  padding: 0.6rem 1rem;
  border-radius: 8px;
  margin: 0;
}

.highlight-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
}

.highlight {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  text-decoration: none;
  color: var(--color-text);
  transition: border-color 0.15s ease;
}

.highlight:hover {
  border-color: var(--color-accent);
}

.highlight.danger {
  border-color: var(--color-danger-fg);
}

.highlight.warn {
  border-color: var(--color-warning-fg);
}

.highlight-value {
  font-size: 1.4rem;
  font-weight: 700;
}

.highlight-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.quick-links {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.link-card {
  text-decoration: none;
  color: var(--color-accent);
  font-weight: 700;
  text-align: center;
}

.link-card:hover {
  border-color: var(--color-accent);
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
