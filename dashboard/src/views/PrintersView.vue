<script setup lang="ts">
import { usePrintersPage } from '../composables/usePrintersPage'
import NamedBarChart from '../components/NamedBarChart.vue'

const { printers, chartItems, loading, error } = usePrintersPage()

function successPercent(rate: number): string {
  return `${Math.round(rate * 1000) / 10}%`
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>

    <NamedBarChart title="Printerlar bo'yicha varaqlar" :items="chartItems" value-label="Varaqlar" />

    <div class="card">
      <h2>Printerlar ro'yxati</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Printer</th>
              <th class="num">Varaqlar</th>
              <th class="num">Buyurtmalar</th>
              <th class="num">Muvaffaqiyat</th>
              <th class="num">Xatoliklar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in printers" :key="p.name">
              <td>{{ p.name }}</td>
              <td class="num">{{ p.pages }}</td>
              <td class="num">{{ p.jobs }}</td>
              <td class="num" :class="{ negative: p.successRate < 0.9 }">{{ successPercent(p.successRate) }}</td>
              <td class="num" :class="{ negative: p.failedJobs > 0 }">{{ p.failedJobs }}</td>
            </tr>
            <tr v-if="!printers.length">
              <td colspan="5" class="empty">Ushbu davr uchun ma'lumot topilmadi</td>
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

.negative {
  color: var(--color-danger-fg);
  font-weight: 700;
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
