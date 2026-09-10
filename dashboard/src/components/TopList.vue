<script setup lang="ts">
import { computed } from 'vue'
import type { TopItem } from '../api/types'
import AppIcon from './AppIcon.vue'

const props = withDefaults(defineProps<{ title: string; items: TopItem[]; icon?: string }>(), {
  icon: 'chart',
})

const maxPages = computed(() => Math.max(1, ...props.items.map((i) => i.pages)))
const numberFormat = new Intl.NumberFormat('uz-UZ')
</script>

<template>
  <section class="panel">
    <header class="panel__head">
      <h2 class="panel__title">
        <span class="panel__title-icon"><AppIcon :name="icon" :size="16" /></span>
        {{ title }}
      </h2>
    </header>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-num">T/r</th>
            <th>Nomi</th>
            <th class="num">Varaqlar</th>
            <th class="num">Ishlar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in items" :key="item.name">
            <td class="col-num">{{ i + 1 }}</td>
            <td>
              <div class="bar-cell">
                <span class="bar-cell__label" :title="item.name">{{ item.name }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: `${(item.pages / maxPages) * 100}%` }" />
                </div>
              </div>
            </td>
            <td class="num strong">{{ numberFormat.format(item.pages) }}</td>
            <td class="num muted">{{ numberFormat.format(item.jobs) }}</td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="4" class="empty">Ma'lumot yo'q</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.bar-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 9rem;
}

.bar-cell__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 18rem;
}
</style>
