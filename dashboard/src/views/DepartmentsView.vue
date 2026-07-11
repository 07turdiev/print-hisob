<script setup lang="ts">
import { useDepartmentsPage } from '../composables/useDepartmentsPage'
import NamedBarChart from '../components/NamedBarChart.vue'
import UsageBar from '../components/UsageBar.vue'

const { departments, departmentChartItems, loading, error } = useDepartmentsPage()
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>

    <NamedBarChart title="Bo'limlar bo'yicha varaqlar" :items="departmentChartItems" value-label="Varaqlar" />

    <div class="card">
      <h2>Bo'limlar</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Bo'lim</th>
              <th class="num">Xodimlar</th>
              <th class="num">Buyurtmalar</th>
              <th>Sarflangan / Kvota (varaq)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in departments" :key="d.name" :class="{ 'row-over': d.overLimit }">
              <td>{{ d.name }}</td>
              <td class="num">{{ d.employeeCount }}</td>
              <td class="num">{{ d.jobs }}</td>
              <td>
                <UsageBar :used="d.pages" :allocated="d.totalAllocated" :over-limit="d.overLimit" />
              </td>
            </tr>
            <tr v-if="!departments.length">
              <td colspan="4" class="empty">Ma'lumot topilmadi</td>
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

.table-wrap {
  overflow-x: auto;
}

.num {
  text-align: right;
}

.row-over {
  background: var(--color-danger-bg);
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
