<script setup lang="ts">
import { computed } from 'vue'
import type { TopItem } from '../api/types'

const props = defineProps<{ title: string; items: TopItem[] }>()

const maxPages = computed(() => Math.max(1, ...props.items.map((i) => i.pages)))
</script>

<template>
  <div class="card">
    <h3>{{ title }}</h3>
    <table>
      <thead>
        <tr>
          <th>Nomi</th>
          <th class="num">Varaqlar</th>
          <th class="num">Buyurtmalar</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.name">
          <td>
            <div class="bar-row">
              <span class="bar-label">{{ item.name }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: `${(item.pages / maxPages) * 100}%` }" />
              </div>
            </div>
          </td>
          <td class="num">{{ item.pages }}</td>
          <td class="num">{{ item.jobs }}</td>
        </tr>
        <tr v-if="!items.length">
          <td colspan="3" class="empty">Ma'lumot yo'q</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.num {
  text-align: right;
}

.bar-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 10rem;
}

.bar-label {
  font-size: 0.85rem;
}

.bar-track {
  height: 5px;
  border-radius: 3px;
  background: var(--color-muted-bg);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--color-accent);
  border-radius: 3px;
}

.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: 1rem;
}
</style>
