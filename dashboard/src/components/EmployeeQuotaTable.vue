<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EmployeeStat } from '../api/types'
import { usePeriodStore } from '../stores/period'
import StatusBadge from './StatusBadge.vue'

const MONTH_NAMES = [
  'Yanvar',
  'Fevral',
  'Mart',
  'Aprel',
  'May',
  'Iyun',
  'Iyul',
  'Avgust',
  'Sentyabr',
  'Oktyabr',
  'Noyabr',
  'Dekabr',
]

const props = withDefaults(defineProps<{ employees: EmployeeStat[]; title?: string }>(), {
  title: "Xodimlar bo'yicha kvota",
})
const emit = defineEmits<{ save: [login: string, allocatedPages: number] }>()

const periodStore = usePeriodStore()

/** e.g. "3-chorak" or "Iyul" — matches the backend's period_label so the quota column
 *  header always states which period is being edited (quotas are per-period rows). */
const periodLabel = computed(() =>
  periodStore.periodType === 'quarter'
    ? `${periodStore.periodNo}-chorak`
    : MONTH_NAMES[periodStore.periodNo - 1] ?? String(periodStore.periodNo),
)

const quotaColumnLabel = computed(() => `Kvota (${periodLabel.value})`)

type SortKey = 'name' | 'position' | 'used' | 'allocated' | 'remaining' | 'percent'

const sortKey = ref<SortKey>('used')
const sortDesc = ref(true)

function percentOf(emp: EmployeeStat): number {
  return emp.allocated > 0 ? (emp.used / emp.allocated) * 100 : emp.used > 0 ? Infinity : 0
}

function setSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDesc.value = !sortDesc.value
  } else {
    sortKey.value = key
    sortDesc.value = true
  }
}

const sortedEmployees = computed(() => {
  const list = [...props.employees]
  const dir = sortDesc.value ? -1 : 1
  list.sort((a, b) => {
    switch (sortKey.value) {
      case 'name':
        return dir * (a.fullName ?? a.login).localeCompare(b.fullName ?? b.login)
      case 'position':
        return dir * (a.position ?? '').localeCompare(b.position ?? '')
      case 'used':
        return dir * (a.used - b.used)
      case 'allocated':
        return dir * (a.allocated - b.allocated)
      case 'remaining':
        return dir * (a.remaining - b.remaining)
      case 'percent':
        return dir * (percentOf(a) - percentOf(b))
      default:
        return 0
    }
  })
  return list
})

const editingLogin = ref<string | null>(null)
const editValue = ref(0)
const saving = ref(false)

function startEdit(emp: EmployeeStat) {
  editingLogin.value = emp.login
  editValue.value = emp.allocated
}

function cancelEdit() {
  editingLogin.value = null
}

async function confirmEdit(login: string) {
  saving.value = true
  try {
    emit('save', login, editValue.value)
  } finally {
    saving.value = false
    editingLogin.value = null
  }
}

function sortIndicator(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortDesc.value ? ' ▼' : ' ▲'
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h2>{{ title }}</h2>
      <slot name="actions" />
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="sortable" @click="setSort('name')">Xodim{{ sortIndicator('name') }}</th>
            <th class="sortable" @click="setSort('position')">Lavozimi{{ sortIndicator('position') }}</th>
            <th>Bo'lim</th>
            <th>Holat</th>
            <th class="sortable num" @click="setSort('used')">Sarflangan (varaq){{ sortIndicator('used') }}</th>
            <th class="sortable num" @click="setSort('allocated')">{{ quotaColumnLabel }}{{ sortIndicator('allocated') }}</th>
            <th class="sortable num" @click="setSort('remaining')">Qoldiq (varaq){{ sortIndicator('remaining') }}</th>
            <th class="sortable num" @click="setSort('percent')">%{{ sortIndicator('percent') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="emp in sortedEmployees"
            :key="emp.login"
            :class="{ 'row-over': emp.overLimit }"
          >
            <td>
              <div class="employee-name">{{ emp.fullName ?? emp.login }}</div>
              <div class="employee-login">{{ emp.login }}</div>
            </td>
            <td>{{ emp.position ?? '—' }}</td>
            <td>{{ emp.department ?? '-' }}</td>
            <td><StatusBadge :status="emp.matchStatus" /></td>
            <td class="num">{{ emp.used }}</td>
            <td class="num">
              <template v-if="editingLogin === emp.login">
                <input
                  v-model.number="editValue"
                  type="number"
                  min="0"
                  class="quota-input"
                  @keyup.enter="confirmEdit(emp.login)"
                  @keyup.escape="cancelEdit"
                />
                <button class="btn btn-primary btn-sm quota-action" :disabled="saving" @click="confirmEdit(emp.login)">Saqlash</button>
                <button class="btn btn-ghost btn-sm quota-action" @click="cancelEdit">Bekor</button>
              </template>
              <template v-else>
                <span class="editable" @click="startEdit(emp)">{{ emp.allocated }}</span>
              </template>
            </td>
            <td class="num" :class="{ negative: emp.remaining < 0 }">{{ emp.remaining }}</td>
            <td class="num">
              <span v-if="emp.allocated > 0">{{ Math.round((emp.used / emp.allocated) * 100) }}%</span>
              <span v-else>-</span>
              <span v-if="emp.overLimit" class="over-tag">limitdan oshgan</span>
            </td>
          </tr>
          <tr v-if="!sortedEmployees.length">
            <td colspan="8" class="empty">Ushbu davr uchun ma'lumot topilmadi</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.card-header h2 {
  margin: 0;
}

th.sortable {
  cursor: pointer;
}

.muted {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.employee-name {
  font-weight: 600;
}

.employee-login {
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.row-over {
  background: var(--color-danger-bg);
}

.negative {
  color: var(--color-danger-fg);
  font-weight: 700;
}

.over-tag {
  display: block;
  font-size: 0.7rem;
  color: var(--color-danger-fg);
  font-weight: 600;
}

.editable {
  border-bottom: 1px dashed var(--color-border-strong);
  cursor: pointer;
  font-weight: 600;
}

.editable:hover {
  color: var(--color-accent-soft-fg);
  border-color: var(--color-accent);
}

.quota-input {
  width: 5rem;
  height: 30px;
  padding: 0 0.4rem;
}

.quota-action {
  margin-left: 0.35rem;
}

.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: 1.5rem;
}
</style>
