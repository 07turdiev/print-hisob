<script setup lang="ts">
import { useEmployeesPage } from '../composables/useEmployeesPage'
import { usePeriodStore } from '../stores/period'
import DepartmentFilter from '../components/DepartmentFilter.vue'
import EmployeeQuotaTable from '../components/EmployeeQuotaTable.vue'
import CsvDownloadButton from '../components/CsvDownloadButton.vue'
import AppIcon from '../components/AppIcon.vue'

const periodStore = usePeriodStore()
const { rows, search, activeFilter, departmentOptions, loading, error, saveQuota } = useEmployeesPage()

function handleSave(login: string, allocatedPages: number) {
  saveQuota(login, allocatedPages).catch(() => {
    // EmployeeQuotaTable already resets its own editing state; errors are non-fatal here.
  })
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>

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
  border-radius: 8px;
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
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  min-width: 9rem;
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
