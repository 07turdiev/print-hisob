<script setup lang="ts">
import { computed } from 'vue'
import type { FailureReason } from '../api/types'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ failures: FailureReason[] }>()

const total = computed(() => props.failures.reduce((sum, f) => sum + f.count, 0))
const maxCount = computed(() => Math.max(1, ...props.failures.map((f) => f.count)))
</script>

<template>
  <section class="panel">
    <header class="panel__head">
      <h2 class="panel__title">
        <span class="panel__title-icon"><AppIcon name="warning" :size="16" /></span>
        Xatoliklar sababi bo'yicha
      </h2>
      <span class="panel__count">Jami: {{ total }}</span>
    </header>

    <div class="panel__body">
      <ul v-if="failures.length" class="failure-list">
        <li v-for="f in failures" :key="f.reason" class="failure">
          <div class="failure__row">
            <span class="failure__text" :title="f.reason">{{ f.reason }}</span>
            <span class="failure__count">{{ f.count }}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill bar-fill--danger" :style="{ width: `${(f.count / maxCount) * 100}%` }" />
          </div>
        </li>
      </ul>

      <div v-else class="empty-state">
        <span class="empty-state__icon"><AppIcon name="check-circle" :size="20" /></span>
        Bu davrda muvaffaqiyatsiz chop etish qayd etilmagan
      </div>
    </div>
  </section>
</template>

<style scoped>
.failure-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.failure__row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  font-size: var(--font-size-base);
  margin-bottom: 4px;
}

.failure__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.failure__count {
  font-weight: 600;
  color: var(--color-danger-fg);
  font-variant-numeric: tabular-nums;
}
</style>
