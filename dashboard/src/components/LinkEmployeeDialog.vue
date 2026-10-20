<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { normalizeLogin } from '../utils/logins'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  /** Kimni biriktirmoqchimiz (F.I.SH. ko'rsatish uchun). */
  employee: { login: string; fullName: string | null } | null
  /** Tanlash uchun xodimlar ro'yxati (AD ro'yxati ham, statistika ham mos keladi). */
  options: { login: string; fullName: string | null; department: string | null }[]
  saving?: boolean
  error?: string | null
}>()

const emit = defineEmits<{ select: [login: string]; close: [] }>()

const search = ref('')

// Oyna har ochilganda qidiruv tozalanadi.
watch(
  () => props.employee,
  () => (search.value = ''),
)

const candidates = computed(() => {
  const self = normalizeLogin(props.employee?.login)
  const query = search.value.trim().toLowerCase()
  return props.options
    .filter((emp) => normalizeLogin(emp.login) !== self)
    .filter((emp) => {
      if (!query) return true
      return (
        emp.login.toLowerCase().includes(query) ||
        (emp.fullName ?? '').toLowerCase().includes(query) ||
        (emp.department ?? '').toLowerCase().includes(query)
      )
    })
    .slice(0, 100)
})
</script>

<template>
  <div v-if="employee" class="backdrop" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-modal="true">
      <header class="dialog__head">
        <h2 class="dialog__title">
          <span class="dialog__icon"><AppIcon name="link" :size="16" /></span>
          Xodimga biriktirish
        </h2>
        <button type="button" class="icon-btn" title="Yopish" @click="emit('close')">
          <AppIcon name="close" :size="16" />
        </button>
      </header>

      <div class="dialog__body">
        <p class="hint">
          <strong>{{ employee.fullName ?? employee.login }}</strong> chiqargan varaqlar
          tanlangan xodimning hisobida ham ko'rsatiladi. Varaqlar ko'chirilmaydi —
          har ikkalasi ham o'z sarfini saqlaydi.
        </p>

        <label class="search-box">
          <AppIcon name="search" :size="15" />
          <input
            v-model="search"
            type="text"
            placeholder="F.I.SH., login yoki bo'lim bo'yicha qidirish"
            autofocus
          />
        </label>

        <p v-if="error" class="alert alert--danger dialog__error">
          <span class="alert__icon"><AppIcon name="warning" :size="15" /></span>
          <span>{{ error }}</span>
        </p>

        <ul v-if="candidates.length" class="candidates">
          <li v-for="emp in candidates" :key="emp.login">
            <button type="button" class="candidate" :disabled="saving" @click="emit('select', emp.login)">
              <span class="candidate__text">
                <span class="candidate__name">{{ emp.fullName ?? emp.login }}</span>
                <span class="candidate__meta">{{ emp.login }} · {{ emp.department ?? '—' }}</span>
              </span>
              <AppIcon name="arrow-right" :size="15" class="candidate__arrow" />
            </button>
          </li>
        </ul>

        <div v-else class="empty-state">
          <span class="empty-state__icon"><AppIcon name="search" :size="18" /></span>
          Mos xodim topilmadi
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 30, 55, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  z-index: 50;
}

.dialog {
  width: 100%;
  max-width: 30rem;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
}

.dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 9px var(--space-4);
  background: var(--color-surface-2);
  border-bottom: 1px solid var(--color-border);
  border-radius: var(--radius) var(--radius) 0 0;
}

.dialog__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.dialog__icon {
  display: inline-flex;
  color: var(--color-accent);
}

.dialog__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  min-height: 0;
}

.hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.hint strong {
  color: var(--color-text);
}

.dialog__error {
  margin: 0;
}

.candidates {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.candidates li + li {
  border-top: 1px solid var(--color-border);
}

.candidate {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
  padding: 8px var(--space-3);
  border: none;
  background: transparent;
  color: var(--color-text);
  text-align: left;
  transition: background-color var(--transition);
}

.candidate:hover:not(:disabled) {
  background: var(--color-accent-soft-bg);
}

.candidate:disabled {
  opacity: 0.6;
}

.candidate__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.candidate__name {
  font-size: var(--font-size-base);
  font-weight: 600;
}

.candidate__meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.candidate__arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.candidate:hover:not(:disabled) .candidate__arrow {
  color: var(--color-accent);
}
</style>
