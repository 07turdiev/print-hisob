<script setup lang="ts">
import { computed } from 'vue'
import type { MatchStatus } from '../api/types'

const props = defineProps<{ status: MatchStatus }>()

const label = computed(() => {
  switch (props.status) {
    case 'active':
      return 'Faol'
    case 'inactive':
      return 'Ketgan'
    case 'unmatched':
      return "Noma'lum"
  }
  return props.status
})
</script>

<template>
  <span class="badge" :class="`badge--${status}`">{{ label }}</span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.badge::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.badge--active {
  background: var(--color-success-bg);
  color: var(--color-success-fg);
}
.badge--inactive {
  background: var(--color-muted-bg);
  color: var(--color-muted-fg);
}
.badge--unmatched {
  background: var(--color-warning-bg);
  color: var(--color-warning-fg);
}
</style>
