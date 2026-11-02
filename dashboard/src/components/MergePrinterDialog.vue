<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { PrinterStat } from '../api/types'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  /** Qaysi printerni boshqasiga qo'shmoqchimiz (`null` — oyna yopiq). */
  source: PrinterStat | null
  /** Tanlash uchun barcha printerlar. */
  options: PrinterStat[]
  /** Server taklif qilgan qurilma — ro'yxatda birinchi turadi va belgilanadi. */
  suggestedId?: number | null
  saving?: boolean
  error?: string | null
}>()

const emit = defineEmits<{ select: [targetId: number]; close: [] }>()

const search = ref('')

watch(
  () => props.source,
  () => (search.value = ''),
)

const numberFormat = new Intl.NumberFormat('uz-UZ')

const candidates = computed(() => {
  const query = search.value.trim().toLowerCase()
  const list = props.options
    .filter((p) => p.deviceId !== null && p.deviceId !== props.source?.deviceId)
    .filter((p) => !query || p.name.toLowerCase().includes(query))

  // Taklif qilingan qurilma tepada turadi — admin uni qidirib yurmasligi uchun.
  const suggested = props.suggestedId
  if (suggested == null) return list
  return [...list].sort((a, b) => Number(b.deviceId === suggested) - Number(a.deviceId === suggested))
})
</script>

<template>
  <div v-if="source" class="backdrop" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-modal="true">
      <header class="dialog__head">
        <h2 class="dialog__title">
          <span class="dialog__icon"><AppIcon name="printers" :size="16" /></span>
          Printerlarni birlashtirish
        </h2>
        <button type="button" class="icon-btn" title="Yopish" @click="emit('close')">
          <AppIcon name="close" :size="16" />
        </button>
      </header>

      <div class="dialog__body">
        <p class="hint">
          <strong>{{ source.name }}</strong> ({{ numberFormat.format(source.pages) }} varaq)
          tanlangan printerga qo'shiladi. Uning barcha nishonlari — MAC, IP va drayver
          nomlari — o'sha printerga ko'chadi va butun tarix bitta nom ostida birlashadi.
          Bu amalni qaytarib bo'lmaydi.
        </p>

        <label class="search-box">
          <AppIcon name="search" :size="15" />
          <input v-model="search" type="text" placeholder="Printer nomi bo'yicha qidirish" autofocus />
        </label>

        <p v-if="error" class="alert alert--danger dialog__error">
          <span class="alert__icon"><AppIcon name="warning" :size="15" /></span>
          <span>{{ error }}</span>
        </p>

        <ul v-if="candidates.length" class="candidates">
          <li v-for="p in candidates" :key="p.deviceId ?? p.name">
            <button
              type="button"
              class="candidate"
              :disabled="saving"
              @click="p.deviceId !== null && emit('select', p.deviceId)"
            >
              <span class="candidate__text">
                <span class="candidate__name">
                  {{ p.name }}
                  <span v-if="p.deviceId === suggestedId" class="candidate__badge">taklif</span>
                </span>
                <span class="candidate__meta">
                  {{ numberFormat.format(p.pages) }} varaq
                  <template v-if="p.lastIp"> · {{ p.lastIp }}</template>
                </span>
              </span>
              <AppIcon name="arrow-right" :size="15" class="candidate__arrow" />
            </button>
          </li>
        </ul>

        <div v-else class="empty-state">
          <span class="empty-state__icon"><AppIcon name="search" :size="18" /></span>
          Mos printer topilmadi
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

.candidate__badge {
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--color-accent);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: 600;
  vertical-align: middle;
}

.candidate__meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.candidate__arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.candidate:hover:not(:disabled) .candidate__arrow {
  color: var(--color-accent);
}
</style>
