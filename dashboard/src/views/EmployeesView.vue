<script setup lang="ts">
import { useEmployeesPage } from '../composables/useEmployeesPage'
import { usePeriodStore } from '../stores/period'
import DepartmentFilter from '../components/DepartmentFilter.vue'
import EmployeeQuotaTable from '../components/EmployeeQuotaTable.vue'
import CsvDownloadButton from '../components/CsvDownloadButton.vue'
import AdSyncBanner from '../components/AdSyncBanner.vue'
import AppIcon from '../components/AppIcon.vue'

const periodStore = usePeriodStore()
const { rows, search, activeFilter, departmentOptions, defaultQuota, adSyncStatus, loading, error, saveQuota } =
  useEmployeesPage()

function handleSave(login: string, allocatedPages: number) {
  saveQuota(login, allocatedPages).catch(() => {
    // EmployeeQuotaTable already resets its own editing state; errors are non-fatal here.
  })
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>

    <AdSyncBanner :status="adSyncStatus" />

    <div class="filters card">
      <label class="search-box">
        <AppIcon name="search" :size="16" />
        <input v-model="search" type="text" placeholder="Login yoki F.I.Sh. bo'yicha qidirish" />
      </label>

      <div class="group">
        <label>Holat</label>
        <select v-model="activeFilter">
          <option value="">Barchasi</option>
          <option value="active">Faol</option>
          <option value="inactive">Ketgan</option>
        </select>
      </div>
    </div>

    <DepartmentFilter :department-options="departmentOptions" />

    <p class="quota-hint">
      Kvota tanlangan davr uchun saqlanadi. Belgilanmagan xodimlarga standart
      <strong>{{ defaultQuota }}</strong> varaq qo'llanadi.
    </p>

    <EmployeeQuotaTable :employees="rows" title="Barcha xodimlar va kvotalar" @save="handleSave">
      <template #actions>
        <CsvDownloadButton
          :period-type="periodStore.periodType"
          :year="periodStore.year"
          :period-no="periodStore.periodNo"
          :department="periodStore.department"
        />
      </template>
    </EmployeeQuotaTable>

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
  border-radius: var(--radius-sm);
  margin: 0;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  align-items: flex-end;
  padding: 0.85rem 1.25rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  min-width: 18rem;
  flex: 1;
  height: 36px;
  transition: border-color var(--transition), box-shadow var(--transition);
}

.search-box:focus-within {
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.search-box input {
  border: none;
  height: auto;
  padding: 0;
  background: transparent;
  color: var(--color-text);
  flex: 1;
  font-size: 0.9rem;
}

.search-box input:focus {
  outline: none;
  box-shadow: none;
}

.group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.group label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.group select {
  min-width: 9rem;
}

.loading-hint {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-pop);
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-pill);
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.quota-hint {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
</style>
