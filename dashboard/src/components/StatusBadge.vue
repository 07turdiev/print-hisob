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
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
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
