<script setup lang="ts" generic="T">
import { computed, ref } from 'vue'
import AppIcon from './AppIcon.vue'

/**
 * Qidiruvli ko'p tanlovli ro'yxat.
 *
 * Tanlanganlar har doim tepada turadi: ro'yxat uzun bo'lganda admin nimani
 * belgilaganini qidirib yurmasligi kerak.
 */
const props = defineProps<{
  items: T[]
  /** Element kaliti (son yoki satr) — tanlov shu bo'yicha saqlanadi. */
  keyOf: (item: T) => string | number
  label: (item: T) => string
  /** Ikkinchi qator — masalan bo'lim yoki IP. */
  sublabel?: (item: T) => string | null
  selected: (string | number)[]
  placeholder?: string
  /** Hech narsa topilmaganda ko'rsatiladigan matn. */
  emptyText?: string
  disabled?: boolean
}>()

const emit = defineEmits<{ 'update:selected': [value: (string | number)[]] }>()

const search = ref('')

const visible = computed(() => {
  const query = search.value.trim().toLowerCase()
  const chosen = new Set(props.selected)
  return props.items
    .filter((item) => !query || props.label(item).toLowerCase().includes(query))
    .sort((a, b) => Number(chosen.has(props.keyOf(b))) - Number(chosen.has(props.keyOf(a))))
})

function isChosen(item: T): boolean {
  return props.selected.includes(props.keyOf(item))
}

function toggle(item: T) {
  if (props.disabled) return
  const key = props.keyOf(item)
  const next = isChosen(item)
    ? props.selected.filter((k) => k !== key)
    : [...props.selected, key]
  emit('update:selected', next)
}

function clearAll() {
  emit('update:selected', [])
}
</script>

<template>
  <div class="picker">
    <div class="picker__head">
      <label class="search-box picker__search">
        <AppIcon name="search" :size="14" />
        <input v-model="search" type="text" :placeholder="placeholder ?? 'Qidirish'" />
      </label>
      <button
        v-if="selected.length"
        type="button"
        class="picker__clear"
        :disabled="disabled"
        @click="clearAll"
      >
        {{ selected.length }} ta tanlangan · tozalash
      </button>
    </div>

    <ul v-if="visible.length" class="picker__list">
      <li v-for="item in visible" :key="keyOf(item)">
        <label class="picker__row" :class="{ 'picker__row--on': isChosen(item) }">
          <input
            type="checkbox"
            :checked="isChosen(item)"
            :disabled="disabled"
            @change="toggle(item)"
          />
          <span class="picker__text">
            <span class="picker__label">{{ label(item) }}</span>
            <span v-if="sublabel?.(item)" class="picker__sub">{{ sublabel(item) }}</span>
          </span>
        </label>
      </li>
    </ul>

    <p v-else class="picker__empty">{{ emptyText ?? 'Hech narsa topilmadi' }}</p>
  </div>
</template>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.picker__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.picker__search {
  flex: 1 1 10rem;
}

.picker__clear {
  padding: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  white-space: nowrap;
}

.picker__clear:hover:not(:disabled) {
  color: var(--color-danger-fg);
  border-color: var(--color-danger-fg);
}

.picker__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 15rem;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.picker__list li + li {
  border-top: 1px solid var(--color-border);
}

.picker__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px var(--space-3);
  cursor: pointer;
  transition: background-color var(--transition);
}

.picker__row:hover {
  background: var(--color-surface-2);
}

.picker__row--on {
  background: var(--color-accent-soft-bg);
}

.picker__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.picker__label {
  font-size: var(--font-size-sm);
}

.picker__sub {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
}

.picker__empty {
  padding: var(--space-3);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  text-align: center;
}
</style>
