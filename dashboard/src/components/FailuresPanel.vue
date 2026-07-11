<script setup lang="ts">
import { computed } from 'vue'
import type { FailureReason } from '../api/types'

const props = defineProps<{ failures: FailureReason[] }>()

const total = computed(() => props.failures.reduce((sum, f) => sum + f.count, 0))
const maxCount = computed(() => Math.max(1, ...props.failures.map((f) => f.count)))
</script>

<template>
  <div class="card">
    <h2>Xatoliklar sababi bo'yicha ({{ total }})</h2>
    <ul class="failure-list">
      <li v-for="f in failures" :key="f.reason">
        <div class="reason-row">
          <span class="reason-text">{{ f.reason }}</span>
          <span class="reason-count">{{ f.count }}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: `${(f.count / maxCount) * 100}%` }" />
        </div>
      </li>
      <li v-if="!failures.length" class="empty">Bu davrda muvaffaqiyatsiz chop etish qayd etilmagan</li>
    </ul>
  </div>
</template>

<style scoped>
.failure-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.reason-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
  margin-bottom: 0.2rem;
}

.reason-count {
  font-weight: 700;
  color: var(--color-danger-fg);
}

.bar-track {
  height: 6px;
  border-radius: 3px;
  background: var(--color-muted-bg);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--color-danger-fg);
}

.empty {
  color: var(--color-text-muted);
  text-align: center;
  padding: 1rem 0;
}
</style>
