<script setup lang="ts">
import { computed } from 'vue'
import { useDepartmentsPage } from '../composables/useDepartmentsPage'
import NamedBarChart from '../components/NamedBarChart.vue'
import UsageBar from '../components/UsageBar.vue'
import AppIcon from '../components/AppIcon.vue'

const { departments, departmentChartItems, loading, error } = useDepartmentsPage()

const numberFormat = new Intl.NumberFormat('uz-UZ')
const fmt = (n: number) => numberFormat.format(n)

/** Jadval ostidagi jamlanma — bo'limlar kesimidagi umumiy holat. */
const totals = computed(() => ({
  employees: departments.value.reduce((s, d) => s + d.employeeCount, 0),
  jobs: departments.value.reduce((s, d) => s + d.jobs, 0),
  pages: departments.value.reduce((s, d) => s + d.pages, 0),
  overLimit: departments.value.filter((d) => d.overLimit).length,
}))
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
    </p>

    <NamedBarChart
      title="Bo'limlar bo'yicha qog'oz sarfi"
      icon="departments"
      :items="departmentChartItems"
      value-label="Varaq"
    />

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="departments" :size="16" /></span>
          Bo'limlar kesimi
        </h2>
        <span class="panel__count">{{ departments.length }} ta bo'lim</span>
      </header>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-num">T/r</th>
              <th>Bo'lim nomi</th>
              <th class="num">Xodimlar</th>
              <th class="num">Buyurtmalar</th>
              <th class="num">Sarflangan</th>
              <th class="col-usage">Kvotaga nisbatan</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(d, i) in departments" :key="d.name" :class="{ 'row-danger': d.overLimit }">
              <td class="col-num">{{ i + 1 }}</td>
              <td class="strong">{{ d.name }}</td>
              <td class="num">{{ fmt(d.employeeCount) }}</td>
              <td class="num">{{ fmt(d.jobs) }}</td>
              <td class="num strong">{{ fmt(d.pages) }}</td>
              <td class="col-usage">
                <UsageBar :used="d.pages" :allocated="d.totalAllocated" :over-limit="d.overLimit" />
              </td>
            </tr>

            <tr v-if="!departments.length">
              <td colspan="6" class="empty">Ma'lumot topilmadi</td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer v-if="departments.length" class="panel__foot">
        <span>
          Jami: <strong class="foot-value">{{ fmt(totals.employees) }}</strong> xodim ·
          <strong class="foot-value">{{ fmt(totals.jobs) }}</strong> buyurtma ·
          <strong class="foot-value">{{ fmt(totals.pages) }}</strong> varaq
        </span>
        <span v-if="totals.overLimit" class="badge badge--danger">
          Limitdan oshgan: {{ totals.overLimit }} ta bo'lim
        </span>
      </footer>
    </section>

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.col-usage {
  width: 12rem;
}

.foot-value {
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}
</style>
