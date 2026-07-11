<script setup lang="ts">
import { onMounted, watch } from 'vue'
import type { PeriodType } from '../api/types'
import { usePeriodStore } from '../stores/period'
import { useDashboardData } from '../composables/useDashboardData'
import DepartmentFilter from '../components/DepartmentFilter.vue'
import KpiCards from '../components/KpiCards.vue'
import EmployeeQuotaTable from '../components/EmployeeQuotaTable.vue'
import CsvDownloadButton from '../components/CsvDownloadButton.vue'
import TimeseriesChart from '../components/TimeseriesChart.vue'
import TopList from '../components/TopList.vue'
import FailuresPanel from '../components/FailuresPanel.vue'
import UnmatchedUsersCard from '../components/UnmatchedUsersCard.vue'

const props = defineProps<{ periodType: PeriodType }>()

const periodStore = usePeriodStore()
watch(() => props.periodType, (pt) => periodStore.setPeriodType(pt), { immediate: true })
onMounted(() => periodStore.setPeriodType(props.periodType))

const {
  summary,
  employees,
  unmatchedEmployees,
  timeseries,
  topStats,
  failures,
  loading,
  error,
  departmentOptions,
  saveQuota,
} = useDashboardData()

function handleQuotaSave(login: string, allocatedPages: number) {
  saveQuota(login, allocatedPages).catch(() => {
    // Error surface is intentionally quiet here; a toast/error banner could be added later.
  })
}
</script>

<template>
  <div class="dashboard">
    <DepartmentFilter :department-options="departmentOptions" />

    <p v-if="error" class="error-banner">{{ error }}</p>

    <KpiCards :summary="summary" />

    <EmployeeQuotaTable :employees="employees" @save="handleQuotaSave">
      <template #actions>
        <CsvDownloadButton
          :period-type="periodStore.periodType"
          :year="periodStore.year"
          :period-no="periodStore.periodNo"
          :department="periodStore.department"
        />
      </template>
    </EmployeeQuotaTable>

    <UnmatchedUsersCard :employees="unmatchedEmployees" />

    <TimeseriesChart :points="timeseries" />

    <div class="top-grid">
      <TopList title="Printerlar bo'yicha eng ko'p" :items="topStats?.printers ?? []" />
      <TopList title="Kompyuterlar bo'yicha eng ko'p" :items="topStats?.computers ?? []" />
      <TopList title="Bo'limlar bo'yicha eng ko'p" :items="topStats?.departments ?? []" />
    </div>

    <FailuresPanel :failures="failures" />

    <p v-if="loading" class="loading-hint">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-width: 1280px;
  margin: 0 auto;
  padding: 1.5rem;
}

.top-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.25rem;
}

.error-banner {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  padding: 0.6rem 1rem;
  border-radius: 8px;
  margin: 0;
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
