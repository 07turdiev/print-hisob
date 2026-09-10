<script setup lang="ts">
import { ref } from 'vue'
import { usePrintersPage } from '../composables/usePrintersPage'
import NamedBarChart from '../components/NamedBarChart.vue'
import AppIcon from '../components/AppIcon.vue'

const { printers, chartItems, loading, error, savingMac, renameErrors, rename } = usePrintersPage()

const numberFormat = new Intl.NumberFormat('uz-UZ')
const fmt = (n: number) => numberFormat.format(n)

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
    // Xato renameErrors orqali ko'rsatiladi; tahrirlash oynasi ochiq qoladi.
  }
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
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
            </tr>
          </thead>
          <tbody>
            <tr v-for="(p, i) in printers" :key="p.mac ?? p.name">
              <td class="col-num">{{ i + 1 }}</td>

              <td>
                <!-- MAC manzili bor printerga do'stona nom qo'yish mumkin -->
                <template v-if="editingMac === p.mac && p.mac">
                  <div class="rename-editor">
                    <input
                      v-model="editValue"
                      type="text"
                      class="rename-input"
                      placeholder="Masalan: 3-qavat, kotibiyat"
                      @keyup.enter="confirmEdit(p.mac)"
                      @keyup.escape="cancelEdit"
                    />
                    <button
                      type="button"
                      class="icon-btn icon-btn--ok"
                      title="Saqlash"
                      :disabled="savingMac === p.mac"
                      @click="confirmEdit(p.mac)"
                    >
                      <AppIcon name="check" :size="15" />
                    </button>
                    <button type="button" class="icon-btn" title="Bekor qilish" @click="cancelEdit">
                      <AppIcon name="close" :size="15" />
                    </button>
                  </div>
                  <p v-if="renameErrors[p.mac]" class="rename-error">{{ renameErrors[p.mac] }}</p>
                </template>

                <template v-else>
                  <div class="printer-name">
                    <span class="strong">{{ p.name }}</span>
                    <button
                      v-if="p.mac"
                      type="button"
                      class="icon-btn icon-btn--tiny"
                      title="Nomni tahrirlash"
                      @click="startEdit(p.mac, p.name)"
                    >
                      <AppIcon name="edit" :size="13" />
                    </button>
                    <span v-else class="badge badge--muted badge--plain" title="MAC aniqlanmagan — nom qo'yib bo'lmaydi">
                      MAC yo'q
                    </span>
                  </div>
                </template>

                <div class="printer-sub">
                  <span v-if="p.mac">{{ p.mac }}</span>
                  <span v-if="p.mac && p.lastIp"> · </span>
                  <span v-if="p.lastIp">{{ p.lastIp }}</span>
                </div>
              </td>

              <td class="num strong">{{ fmt(p.pages) }}</td>
              <td class="num">{{ fmt(p.jobs) }}</td>
              <td class="num" :class="{ negative: p.successRate < 0.9 }">{{ successPercent(p.successRate) }}</td>
              <td class="num" :class="{ negative: p.failedJobs > 0 }">{{ fmt(p.failedJobs) }}</td>
            </tr>

            <tr v-if="!printers.length">
              <td colspan="6" class="empty">Ushbu davr uchun ma'lumot topilmadi</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.printer-name {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.printer-sub {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}

.icon-btn--tiny {
  width: 22px;
  height: 22px;
}

.icon-btn--ok:hover {
  color: var(--color-success-fg);
  background: var(--color-success-bg);
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

.rename-error {
  margin-top: 4px;
  color: var(--color-danger-fg);
  font-size: var(--font-size-xs);
}
</style>
