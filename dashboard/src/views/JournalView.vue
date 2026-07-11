<script setup lang="ts">
import { useJournalPage } from '../composables/useJournalPage'
import StatusBadge from '../components/StatusBadge.vue'

const {
  computer,
  user,
  printer,
  success,
  since,
  until,
  page,
  totalPages,
  jobs,
  total,
  loading,
  error,
  matchStatusFor,
  nextPage,
  prevPage,
} = useJournalPage()

const dateTimeFormat = new Intl.DateTimeFormat('uz-UZ', { dateStyle: 'medium', timeStyle: 'short' })

function formatTimestamp(iso: string): string {
  try {
    return dateTimeFormat.format(new Date(iso))
  } catch {
    return iso
  }
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="error-banner">{{ error }}</p>

    <div class="filters card">
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
        <input v-model="printer" type="text" placeholder="Printer nomi" />
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
    </div>

    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sana</th>
              <th>Foydalanuvchi</th>
              <th>Kompyuter</th>
              <th>Hujjat</th>
              <th>Printer</th>
              <th class="num" title="Varaqlar = sarflangan qog'oz">Varaqlar</th>
              <th class="num" title="Sahifalar = hujjatdagi betlar">Sahifalar</th>
              <th>2 tomonlama</th>
              <th>Holat</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in jobs" :key="job.id" :class="{ 'row-fail': !job.success }">
              <td class="nowrap">{{ formatTimestamp(job.timestamp) }}</td>
              <td>
                <div class="user-cell">
                  <span>{{ job.user }}</span>
                  <StatusBadge :status="matchStatusFor(job.user)" />
                </div>
              </td>
              <td>{{ job.computer }}</td>
              <td class="doc-cell">{{ job.document }}</td>
              <td>
                <div>{{ job.printer }}</div>
                <div class="muted">{{ job.printerIp }}</div>
              </td>
              <td class="num">{{ job.pages }}</td>
              <td class="num">{{ job.documentPages }}</td>
              <td class="duplex-cell">
                <span v-if="job.duplex" class="duplex-yes">Ha</span>
                <span v-else class="duplex-no">Yo'q</span>
              </td>
              <td>
                <span v-if="job.success" class="ok-tag">Muvaffaqiyatli</span>
                <span v-else class="fail-tag">{{ job.reason ?? 'Xatolik' }}</span>
              </td>
            </tr>
            <tr v-if="!jobs.length">
              <td colspan="9" class="empty">Filtrlarga mos yozuvlar topilmadi</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <span class="total-hint">Jami: {{ total }} ta yozuv</span>
        <div class="pager">
          <button type="button" :disabled="page <= 1" @click="prevPage">&larr; Oldingi</button>
          <span>{{ page }} / {{ totalPages }}</span>
          <button type="button" :disabled="page >= totalPages" @click="nextPage">Keyingi &rarr;</button>
        </div>
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
  border-radius: 8px;
  margin: 0;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 0.85rem 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.field input,
.field select {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  font-weight: 400;
  font-size: 0.88rem;
  min-width: 8.5rem;
}

.table-wrap {
  overflow-x: auto;
}

.num {
  text-align: right;
}

.nowrap {
  white-space: nowrap;
}

.doc-cell {
  max-width: 14rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.muted {
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.row-fail {
  background: var(--color-danger-bg);
}

.duplex-cell {
  text-align: center;
}

.duplex-yes {
  color: var(--color-accent);
  font-weight: 600;
  font-size: 0.82rem;
}

.duplex-no {
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.ok-tag {
  color: var(--color-success-fg);
  font-weight: 600;
  font-size: 0.82rem;
}

.fail-tag {
  color: var(--color-danger-fg);
  font-weight: 600;
  font-size: 0.82rem;
}

.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: 1.5rem;
}

.pagination {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.pager {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.pager button {
  padding: 0.35rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.85rem;
}

.pager button:disabled {
  opacity: 0.5;
  cursor: default;
}

.loading-hint {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
</style>
