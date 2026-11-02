<script setup lang="ts">
import { ref } from 'vue'
import type { PrinterRow } from '../composables/usePrintersPage'
import { usePrintersPage } from '../composables/usePrintersPage'
import NamedBarChart from '../components/NamedBarChart.vue'
import AppIcon from '../components/AppIcon.vue'
import MergePrinterDialog from '../components/MergePrinterDialog.vue'

const {
  printers,
  chartItems,
  loading,
  error,
  savingId,
  rowErrors,
  suggestionCount,
  nameOf,
  rename,
  merge,
} = usePrintersPage()

const numberFormat = new Intl.NumberFormat('uz-UZ')
const fmt = (n: number) => numberFormat.format(n)

function successPercent(rate: number): string {
  return `${Math.round(rate * 1000) / 10}%`
}

// --- Nom o'zgartirish ---
const editingId = ref<number | null>(null)
const editValue = ref('')

function startEdit(printer: PrinterRow) {
  if (printer.deviceId === null) return
  editingId.value = printer.deviceId
  editValue.value = printer.name
}

function cancelEdit() {
  editingId.value = null
}

async function confirmEdit(deviceId: number) {
  try {
    await rename(deviceId, editValue.value.trim())
    editingId.value = null
  } catch {
    // Xato qator ostida ko'rsatiladi; tahrirlash oynasi ochiq qoladi.
  }
}

// --- Birlashtirish ---
const mergeSource = ref<PrinterRow | null>(null)
/** Taklifdan kelgan bo'lsa shu qurilma oynada birinchi turadi. */
const mergeSuggestedId = ref<number | null>(null)

function startMerge(printer: PrinterRow, suggestedId: number | null = null) {
  mergeSource.value = printer
  mergeSuggestedId.value = suggestedId
}

async function confirmMerge(targetId: number) {
  const source = mergeSource.value
  if (!source || source.deviceId === null) return
  try {
    await merge(targetId, source.deviceId)
    mergeSource.value = null
  } catch {
    // Xato oynada ko'rsatiladi.
  }
}

function mergeError(): string | null {
  const id = mergeSource.value?.deviceId
  return id != null ? rowErrors[id] ?? null : null
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
    </p>

    <p class="alert alert--info">
      <span class="alert__icon"><AppIcon name="info" :size="16" /></span>
      <span>
        Bitta printer turli kompyuterlarda har xil nom bilan ko'rinishi mumkin. Tizim ularni
        MAC yoki IP bo'yicha birlashtiradi; baribir ikki qator bo'lib qolsa, birlashtirish
        tugmasidan foydalaning.
      </span>
    </p>

    <p v-if="suggestionCount" class="alert alert--warning">
      <span class="alert__icon"><AppIcon name="link" :size="16" /></span>
      <span>
        {{ suggestionCount }} ta qatorda ehtimoliy juft topildi — ular bir xil drayver nomi
        bilan kelgan. Taklif qator ostida ko'rsatilgan; birlashtirishni o'zingiz tasdiqlaysiz.
      </span>
    </p>

    <NamedBarChart
      title="Printerlar bo'yicha qog'oz sarfi"
      icon="printers"
      :items="chartItems"
      value-label="Varaq"
    />

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="printers" :size="16" /></span>
          Printerlar ro'yxati
        </h2>
        <span class="panel__count">{{ printers.length }} ta qurilma</span>
      </header>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-num">T/r</th>
              <th>Printer</th>
              <th class="num">Varaqlar</th>
              <th class="num">Ishlar</th>
              <th class="num">Muvaffaqiyat</th>
              <th class="num">Xato</th>
              <th class="col-actions">Amallar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(p, i) in printers" :key="p.deviceId ?? p.name">
              <td class="col-num">{{ i + 1 }}</td>

              <td>
                <template v-if="editingId === p.deviceId && p.deviceId !== null">
                  <div class="rename-editor">
                    <input
                      v-model="editValue"
                      type="text"
                      class="rename-input"
                      placeholder="Masalan: 3-qavat, kotibiyat"
                      @keyup.enter="confirmEdit(p.deviceId)"
                      @keyup.escape="cancelEdit"
                    />
                    <button
                      type="button"
                      class="icon-btn icon-btn--ok"
                      title="Saqlash"
                      :disabled="savingId === p.deviceId"
                      @click="confirmEdit(p.deviceId)"
                    >
                      <AppIcon name="check" :size="15" />
                    </button>
                    <button type="button" class="icon-btn" title="Bekor qilish" @click="cancelEdit">
                      <AppIcon name="close" :size="15" />
                    </button>
                  </div>
                </template>

                <template v-else>
                  <div class="strong">{{ p.name }}</div>
                </template>

                <div class="printer-sub">
                  <span v-if="p.mac">{{ p.mac }}</span>
                  <span v-if="p.mac && p.lastIp"> · </span>
                  <span v-if="p.lastIp">{{ p.lastIp }}</span>
                  <span v-if="!p.mac && !p.lastIp" class="muted">nom bo'yicha aniqlangan</span>
                </div>

                <p v-if="p.suggestion" class="suggest">
                  <AppIcon name="link" :size="13" class="suggest__icon" />
                  <span>
                    Ehtimol <strong>{{ nameOf(p.suggestion.targetId) }}</strong> bilan bir xil
                    printer — ikkisi ham
                    <span class="suggest__name">{{ p.suggestion.sharedName }}</span>
                    nomi bilan kelgan.
                  </span>
                  <button
                    type="button"
                    class="suggest__btn"
                    :disabled="savingId === p.deviceId"
                    @click="startMerge(p, p.suggestion.targetId)"
                  >
                    Ko'rib chiqish
                  </button>
                </p>

                <p v-if="p.deviceId !== null && rowErrors[p.deviceId]" class="row-error">
                  {{ rowErrors[p.deviceId] }}
                </p>
              </td>

              <td class="num strong">{{ fmt(p.pages) }}</td>
              <td class="num">{{ fmt(p.jobs) }}</td>
              <td class="num" :class="{ negative: p.successRate < 0.9 }">
                {{ successPercent(p.successRate) }}
              </td>
              <td class="num" :class="{ negative: p.failedJobs > 0 }">{{ fmt(p.failedJobs) }}</td>

              <td class="col-actions">
                <div class="actions">
                  <button
                    type="button"
                    class="icon-btn"
                    :disabled="p.deviceId === null || savingId === p.deviceId"
                    title="Nomni o'zgartirish"
                    @click="startEdit(p)"
                  >
                    <AppIcon name="edit" :size="15" />
                  </button>
                  <button
                    type="button"
                    class="icon-btn"
                    :disabled="p.deviceId === null || savingId === p.deviceId"
                    title="Boshqa printerga qo'shish"
                    @click="startMerge(p)"
                  >
                    <AppIcon name="link" :size="15" />
                  </button>
                </div>
              </td>
            </tr>

            <tr v-if="!printers.length">
              <td colspan="7" class="empty">Ushbu davr uchun ma'lumot topilmadi</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <MergePrinterDialog
      :source="mergeSource"
      :options="printers"
      :suggested-id="mergeSuggestedId"
      :saving="savingId !== null"
      :error="mergeError()"
      @select="confirmMerge"
      @close="mergeSource = null"
    />

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.col-actions {
  width: 5.5rem;
  text-align: center;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.printer-sub {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}

.rename-editor {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-wrap: wrap;
}

.rename-input {
  height: 26px;
  min-width: 14rem;
}

.row-error {
  margin-top: 4px;
  color: var(--color-danger-fg);
  font-size: var(--font-size-xs);
}

.suggest {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  margin-top: 5px;
  padding: 4px 7px;
  border-left: 2px solid var(--color-accent);
  background: var(--color-accent-soft-bg);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  line-height: 1.45;
}

.suggest__icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--color-accent);
}

.suggest strong {
  color: var(--color-text);
}

.suggest__name {
  font-variant-numeric: tabular-nums;
  color: var(--color-text);
}

.suggest__btn {
  flex-shrink: 0;
  margin-left: auto;
  padding: 2px 8px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-accent);
  font-size: var(--font-size-xs);
  font-weight: 600;
  white-space: nowrap;
  transition: background-color var(--transition);
}

.suggest__btn:hover:not(:disabled) {
  background: var(--color-accent);
  color: #fff;
}

.suggest__btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.icon-btn--ok:hover:not(:disabled) {
  color: var(--color-success-fg);
  background: var(--color-success-bg);
}

.icon-btn:disabled {
  opacity: 0.45;
  cursor: default;
}
</style>
