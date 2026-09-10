<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

/**
 * Bitta ko'rsatkich kartochkasi (KPI).
 * Chap chekkasidagi rangli chiziq ko'rsatkich holatini bildiradi:
 * accent — odatiy, success — yaxshi, warning — e'tibor talab, danger — muammo.
 */
const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    icon?: string
    tone?: 'accent' | 'success' | 'warning' | 'danger' | 'muted'
    hint?: string
    to?: string
  }>(),
  { tone: 'accent' },
)

const tag = computed(() => (props.to ? RouterLink : 'div'))
</script>

<template>
  <component :is="tag" :to="to" class="stat" :class="[`stat--${tone}`, { 'stat--link': to }]">
    <div class="stat__row">
      <span class="stat__label">{{ label }}</span>
      <span v-if="icon" class="stat__icon"><AppIcon :name="icon" :size="16" /></span>
    </div>
    <div class="stat__value">{{ value }}</div>
    <div v-if="hint" class="stat__hint">{{ hint }}</div>
  </component>
</template>

<style scoped>
.stat {
  display: block;
  padding: 10px var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-accent);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  color: var(--color-text);
  text-decoration: none;
  min-width: 0;
}

.stat--link {
  transition: border-color var(--transition), box-shadow var(--transition);
}

.stat--link:hover {
  border-color: var(--color-border-strong);
  border-left-color: var(--color-accent);
  box-shadow: var(--shadow-pop);
  text-decoration: none;
}

.stat__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.stat__label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat__icon {
  display: inline-flex;
  flex-shrink: 0;
  color: var(--color-accent);
}

.stat__value {
  margin-top: 3px;
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat__hint {
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Holat ranglari — chiziq, ikonka va qiymat bir xil rangda */
.stat--success {
  border-left-color: var(--color-success-fg);
}

.stat--success .stat__icon,
.stat--success .stat__value {
  color: var(--color-success-fg);
}

.stat--warning {
  border-left-color: var(--color-warning-fg);
}

.stat--warning .stat__icon,
.stat--warning .stat__value {
  color: var(--color-warning-fg);
}

.stat--danger {
  border-left-color: var(--color-danger-fg);
}

.stat--danger .stat__icon,
.stat--danger .stat__value {
  color: var(--color-danger-fg);
}

.stat--muted {
  border-left-color: var(--color-border-strong);
}

.stat--muted .stat__icon {
  color: var(--color-text-muted);
}
</style>
