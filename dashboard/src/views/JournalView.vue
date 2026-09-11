<script setup lang="ts">
import { computed } from 'vue'
import { useJournalPage } from '../composables/useJournalPage'
import StatusBadge from '../components/StatusBadge.vue'
import AppIcon from '../components/AppIcon.vue'

const {
  computer,
  user,
  printer,
  success,
  since,
  until,
  page,
  pageSize,
  totalPages,
  jobs,
  total,
  loading,
  error,
  matchStatusFor,
  nextPage,
  prevPage,
} = useJournalPage()

const dateTimeFormat = new Intl.DateTimeFormat('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })
const numberFormat = new Intl.NumberFormat('uz-UZ')

function formatTimestamp(iso: string): string {
  try {
    return dateTimeFormat.format(new Date(iso))
  } catch {
    return iso
  }
}

/** Joriy sahifadagi yozuvlar oralig'i, masalan "26–50 / 340". */
const rangeLabel = computed(() => {
  if (!total.value) return '0'
  const from = (page.value - 1) * pageSize.value + 1
  const to = Math.min(total.value, from + jobs.value.length - 1)
  return `${numberFormat.format(from)}–${numberFormat.format(to)} / ${numberFormat.format(total.value)}`
})

const hasFilters = computed(
  () =>
    Boolean(computer.value || user.value || printer.value || success.value || since.value || until.value),
)

function clearFilters() {
  computer.value = ''
  user.value = ''
  printer.value = ''
  success.value = ''
  since.value = ''
  until.value = ''
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
    </p>

    <div class="filter-bar">
      <label class="field">
        <span>Foydalanuvchi</span>
        <input v-model="user" type="text" placeholder="login" />
      </label>
      <label class="field">
        <span>Kompyuter</span>
        <input v-model="computer" type="text" placeholder="PC nomi" />
      </label>
      <label class="field">
        <span>Printer</span>
        <input v-model="printer" type="text" placeholder="Nom yoki uning bir qismi" title="Reyestrdagi nom ham, drayver nomi ham qidiriladi" />
      </label>
      <label class="field">
        <span>Holat</span>
        <select v-model="success">
          <option value="">Barchasi</option>
          <option value="true">Muvaffaqiyatli</option>
          <option value="false">Xatolik</option>
        </select>
      </label>
      <label class="field">
        <span>Sanadan</span>
        <input v-model="since" type="date" />
      </label>
      <label class="field">
        <span>Sanagacha</span>
        <input v-model="until" type="date" />
      </label>

      <button type="button" class="btn clear-btn" :disabled="!hasFilters" @click="clearFilters">
        <AppIcon name="close" :size="14" />
        Tozalash
      </button>
    </div>

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="journal" :size="16" /></span>
          Chop etish hodisalari
        </h2>
        <span class="panel__count">{{ rangeLabel }}</span>
      </header>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-num">T/r</th>
              <th>Sana va vaqt</th>
              <th>Foydalanuvchi</th>
              <th>Kompyuter</th>
              <th>Hujjat</th>
              <th>Printer</th>
              <th class="num" title="Sarflangan qog'oz (varaq) soni">Varaq</th>
              <th class="num" title="Hujjatdagi sahifalar soni">Sahifa</th>
              <th class="col-center">2 tomonlama</th>
              <th>Natija</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(job, i) in jobs" :key="job.id" :class="{ 'row-danger': !job.success }">
              <td class="col-num">{{ (page - 1) * pageSize + i + 1 }}</td>
              <td class="nowrap">{{ formatTimestamp(job.timestamp) }}</td>
              <td>
                <div class="user-cell">
                  <span class="strong">{{ job.user }}</span>
                  <StatusBadge :status="matchStatusFor(job.user)" />
                </div>
              </td>
              <td class="nowrap">{{ job.computer }}</td>
              <td class="doc-cell" :title="job.document">{{ job.document }}</td>
              <!--
                Printer nomi reyestrdan (MAC bo'yicha) olinadi: bitta jismoniy printer
                har bir kompyuterda boshqacha drayver nomi bilan ko'ringan bo'lsa ham,
                jurnalda hamma joyda admin belgilagan yagona nom chiqadi. Xom drayver
                nomi faqat u farq qilganda, ikkinchi qatorda ko'rsatiladi.
              -->
              <td>
                <div class="strong">{{ job.printerName ?? job.printer }}</div>
                <div class="muted">
                  <span v-if="job.printerName && job.printerName !== job.printer" :title="`Ushbu kompyuterdagi drayver nomi: ${job.printer}`">
                    {{ job.printer }}
                  </span>
                  <span v-if="job.printerName && job.printerName !== job.printer && (job.printerIp || job.printerMac)"> · </span>
                  <span v-if="job.printerIp">{{ job.printerIp }}</span>
                  <span v-if="job.printerIp && job.printerMac"> · </span>
                  <span v-if="job.printerMac">{{ job.printerMac }}</span>
                </div>
              </td>
              <td class="num strong">{{ job.pages }}</td>
              <td class="num muted">{{ job.documentPages }}</td>
              <td class="col-center">
                <span v-if="job.duplex" class="badge badge--accent badge--plain">Ha</span>
                <span v-else class="muted">—</span>
              </td>
              <td>
                <span v-if="job.success" class="badge badge--success">Muvaffaqiyatli</span>
                <span v-else class="badge badge--danger" :title="job.reason ?? 'Xatolik'">
                  <span class="reason-text">{{ job.reason ?? 'Xatolik' }}</span>
                </span>
              </td>
            </tr>

            <tr v-if="!jobs.length">
              <td colspan="10" class="empty">Filtrlarga mos yozuvlar topilmadi</td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="panel__foot">
        <span>Jami: <strong class="foot-value">{{ numberFormat.format(total) }}</strong> ta yozuv</span>
        <div class="pager">
          <button type="button" class="btn btn-sm" :disabled="page <= 1" @click="prevPage">
            <AppIcon name="chevron-left" :size="13" />
            Oldingi
          </button>
          <span class="pager__label">{{ page }} / {{ totalPages }}</span>
          <button type="button" class="btn btn-sm" :disabled="page >= totalPages" @click="nextPage">
            Keyingi
            <AppIcon name="chevron-right" :size="13" />
          </button>
        </div>
      </footer>
    </section>

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.clear-btn {
  margin-left: auto;
}

.col-center {
  text-align: center;
}

.doc-cell {
  max-width: 16rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

/* Uzun xatolik matni ustunni cho'zmasin */
.reason-text {
  display: inline-block;
  max-width: 13rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

.foot-value {
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}
</style>
