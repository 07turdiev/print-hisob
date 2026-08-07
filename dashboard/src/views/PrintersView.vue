<script setup lang="ts">
import { ref } from 'vue'
import { usePrintersPage } from '../composables/usePrintersPage'
import NamedBarChart from '../components/NamedBarChart.vue'
import AppIcon from '../components/AppIcon.vue'

const { printers, chartItems, loading, error, savingMac, renameErrors, rename } = usePrintersPage()

function successPercent(rate: number): string {
  return `${Math.round(rate * 1000) / 10}%`
}

const editingMac = ref<string | null>(null)
const editValue = ref('')

function startEdit(mac: string, currentName: string) {
  editingMac.value = mac
  editValue.value = currentName
}

function cancelEdit() {
  editingMac.value = null
}

async function confirmEdit(mac: string) {
  try {
    await rename(mac, editValue.value.trim())
    editingMac.value = null
  } catch {
    // Error is surfaced inline via renameErrors; keep the editor open so the user can retry.
  }
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>

    <NamedBarChart title="Printerlar bo'yicha varaqlar" :items="chartItems" value-label="Varaqlar" />

    <div class="card">
      <h2>Printerlar ro'yxati</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Printer</th>
              <th class="num">Varaqlar</th>
              <th class="num">Ishlar</th>
              <th class="num">Muvaffaqiyat</th>
              <th class="num">Xato</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in printers" :key="p.mac ?? p.name">
              <td>
                <template v-if="editingMac === p.mac && p.mac">
                  <div class="rename-editor">
                    <input
                      v-model="editValue"
                      type="text"
                      class="rename-input"
                      @keyup.enter="confirmEdit(p.mac)"
                      @keyup.escape="cancelEdit"
                    />
                    <button
                      type="button"
                      class="btn btn-primary btn-sm quota-action"
                      :disabled="savingMac === p.mac"
                      @click="confirmEdit(p.mac)"
                    >
                      Saqlash
                    </button>
                    <button type="button" class="btn btn-ghost btn-sm quota-action" @click="cancelEdit">Bekor</button>
                  </div>
                  <p v-if="renameErrors[p.mac]" class="rename-error">{{ renameErrors[p.mac] }}</p>
                </template>
                <template v-else>
                  <div class="printer-name">
                    <span>{{ p.name }}</span>
                    <button
                      v-if="p.mac"
                      type="button"
                      class="edit-btn"
                      title="Nomni tahrirlash"
                      @click="startEdit(p.mac, p.name)"
                    >
                      <AppIcon name="edit" :size="14" />
                    </button>
                    <span v-else class="no-mac-hint" title="MAC yo'q — nom qo'yib bo'lmaydi">MAC yo'q</span>
                  </div>
                </template>
                <div class="printer-sub">
                  <span v-if="p.mac">{{ p.mac }}</span>
                  <span v-if="p.mac && p.lastIp"> &middot; </span>
                  <span v-if="p.lastIp">{{ p.lastIp }}</span>
                </div>
              </td>
              <td class="num">{{ p.pages }}</td>
              <td class="num">{{ p.jobs }}</td>
              <td class="num" :class="{ negative: p.successRate < 0.9 }">{{ successPercent(p.successRate) }}</td>
              <td class="num" :class="{ negative: p.failedJobs > 0 }">{{ p.failedJobs }}</td>
            </tr>
            <tr v-if="!printers.length">
              <td colspan="5" class="empty">Ushbu davr uchun ma'lumot topilmadi</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p v-if="loading" class="loading-hint">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-width: 1280px;
  margin: 0 auto;
  padding: 1.5rem;
}

.error-banner {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  padding: 0.6rem 1rem;
  border-radius: var(--radius-sm);
  margin: 0;
}

.negative {
  color: var(--color-danger-fg);
  font-weight: 700;
}

.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: 1.5rem;
}

.printer-name {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
}

.printer-sub {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  margin-top: 0.15rem;
}

.edit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.15rem;
  border-radius: var(--radius-sm);
  line-height: 0;
}

.edit-btn:hover {
  color: var(--color-accent-soft-fg);
  background: var(--color-accent-soft-bg);
}

.no-mac-hint {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  font-weight: 500;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-pill);
  padding: 0.05rem 0.5rem;
}

.rename-editor {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.rename-input {
  height: 30px;
  padding: 0 0.5rem;
  min-width: 12rem;
}

.quota-action {
  white-space: nowrap;
}

.rename-error {
  margin: 0.3rem 0 0;
  color: var(--color-danger-fg);
  font-size: 0.78rem;
}

.loading-hint {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-pop);
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-pill);
  color: var(--color-text-muted);
  font-size: 0.82rem;
}
</style>
