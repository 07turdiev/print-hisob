<script setup lang="ts">
import { onMounted, watch } from 'vue'
import type { PeriodType } from '../api/types'
import { usePeriodStore } from '../stores/period'
import { useDashboardData } from '../composables/useDashboardData'
import AppIcon from '../components/AppIcon.vue'
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
    // Xatolik bo'lsa jadval o'z holatini tiklaydi; bu yerda ovoz chiqarmaymiz.
  })
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
    </p>

    <div class="filter-bar">
      <span class="filter-bar__icon"><AppIcon name="filter" :size="15" /></span>
      <DepartmentFilter :department-options="departmentOptions" />
    </div>

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

    <div class="grid-3">
      <TopList title="Eng ko'p ishlatilgan printerlar" icon="printers" :items="topStats?.printers ?? []" />
      <TopList title="Eng ko'p chop etgan kompyuterlar" icon="agents" :items="topStats?.computers ?? []" />
      <TopList title="Eng ko'p chop etgan bo'limlar" icon="departments" :items="topStats?.departments ?? []" />
    </div>

    <FailuresPanel :failures="failures" />

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.filter-bar__icon {
  display: inline-flex;
  align-items: center;
  height: 32px;
  color: var(--color-text-muted);
}
</style>
