<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EmployeeStat } from '../api/types'
import { usePeriodStore } from '../stores/period'
import AppIcon from './AppIcon.vue'
import StatusBadge from './StatusBadge.vue'
import UsageBar from './UsageBar.vue'

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
const numberFormat = new Intl.NumberFormat('uz-UZ')
const fmt = (n: number) => numberFormat.format(n)

/** Masalan "3-chorak" yoki "Iyul" — backend'dagi period_label bilan bir xil.
 *  Kvota har davr uchun alohida saqlangani uchun ustun sarlavhasida davr yoziladi. */
const periodLabel = computed(() =>
  periodStore.periodType === 'quarter'
    ? `${periodStore.periodNo}-chorak`
    : MONTH_NAMES[periodStore.periodNo - 1] ?? String(periodStore.periodNo),
)

const quotaColumnLabel = computed(() => `Kvota (${periodLabel.value})`)

type SortKey = 'name' | 'position' | 'department' | 'used' | 'allocated' | 'remaining' | 'percent'

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

function sortCaret(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortDesc.value ? '▼' : '▲'
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
      case 'department':
        return dir * (a.department ?? '').localeCompare(b.department ?? '')
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

/** Jadval ostidagi jamlanma — hisobotni tekshirishda qulay. */
const totals = computed(() => ({
  used: props.employees.reduce((sum, e) => sum + e.used, 0),
  allocated: props.employees.reduce((sum, e) => sum + e.allocated, 0),
  overLimit: props.employees.filter((e) => e.overLimit).length,
}))

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

function confirmEdit(login: string) {
  saving.value = true
  try {
    emit('save', login, editValue.value)
  } finally {
    saving.value = false
    editingLogin.value = null
  }
}
</script>

<template>
  <section class="panel">
    <header class="panel__head">
      <h2 class="panel__title">
        <span class="panel__title-icon"><AppIcon name="employees" :size="16" /></span>
        {{ title }}
      </h2>
      <div class="panel__actions">
        <span class="panel__count">{{ employees.length }} ta xodim</span>
        <slot name="actions" />
      </div>
    </header>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-num">T/r</th>
            <th class="sortable" @click="setSort('name')">
              F.I.SH. <span class="sort-caret">{{ sortCaret('name') }}</span>
            </th>
            <th class="sortable" @click="setSort('position')">
              Lavozimi <span class="sort-caret">{{ sortCaret('position') }}</span>
            </th>
            <th class="sortable" @click="setSort('department')">
              Bo'lim <span class="sort-caret">{{ sortCaret('department') }}</span>
            </th>
            <th>Holat</th>
            <th class="sortable num" @click="setSort('used')">
              Sarflangan <span class="sort-caret">{{ sortCaret('used') }}</span>
            </th>
            <th class="sortable num" @click="setSort('allocated')">
              {{ quotaColumnLabel }} <span class="sort-caret">{{ sortCaret('allocated') }}</span>
            </th>
            <th class="sortable num" @click="setSort('remaining')">
              Qoldiq <span class="sort-caret">{{ sortCaret('remaining') }}</span>
            </th>
            <th class="sortable col-usage" @click="setSort('percent')">
              Bajarilishi <span class="sort-caret">{{ sortCaret('percent') }}</span>
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(emp, i) in sortedEmployees" :key="emp.login" :class="{ 'row-danger': emp.overLimit }">
            <td class="col-num">{{ i + 1 }}</td>

            <td>
              <div class="strong">{{ emp.fullName ?? emp.login }}</div>
              <div class="muted">{{ emp.login }}</div>
            </td>

            <td>{{ emp.position ?? '—' }}</td>
            <td>{{ emp.department ?? '—' }}</td>
            <td><StatusBadge :status="emp.matchStatus" /></td>

            <td class="num strong">{{ fmt(emp.used) }}</td>

            <!-- Kvota — joyida tahrirlanadi -->
            <td class="num">
              <div v-if="editingLogin === emp.login" class="quota-edit">
                <input
                  v-model.number="editValue"
                  type="number"
                  min="0"
                  class="quota-input"
                  @keyup.enter="confirmEdit(emp.login)"
                  @keyup.escape="cancelEdit"
                />
                <button
                  type="button"
                  class="icon-btn icon-btn--ok"
                  title="Saqlash"
                  :disabled="saving"
                  @click="confirmEdit(emp.login)"
                >
                  <AppIcon name="check" :size="15" />
                </button>
                <button type="button" class="icon-btn" title="Bekor qilish" @click="cancelEdit">
                  <AppIcon name="close" :size="15" />
                </button>
              </div>

              <button v-else type="button" class="quota-value" title="Kvotani o'zgartirish" @click="startEdit(emp)">
                {{ fmt(emp.allocated) }}
                <AppIcon name="edit" :size="13" />
              </button>
            </td>

            <td class="num" :class="{ negative: emp.remaining < 0 }">{{ fmt(emp.remaining) }}</td>

            <td class="col-usage">
              <UsageBar :used="emp.used" :allocated="emp.allocated" :over-limit="emp.overLimit" />
            </td>
          </tr>

          <tr v-if="!sortedEmployees.length">
            <td colspan="9" class="empty">Ushbu davr uchun ma'lumot topilmadi</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="employees.length" class="panel__foot">
      <span>
        Jami sarflangan: <strong class="foot-value">{{ fmt(totals.used) }}</strong> varaq &nbsp;·&nbsp;
        Jami kvota: <strong class="foot-value">{{ fmt(totals.allocated) }}</strong> varaq
      </span>
      <span v-if="totals.overLimit" class="badge badge--danger">
        Limitdan oshgan: {{ totals.overLimit }} ta xodim
      </span>
      <span v-else class="badge badge--success">Limitdan oshgan xodim yo'q</span>
    </footer>
  </section>
</template>

<style scoped>
.col-usage {
  width: 11rem;
}

/* Kvota qiymati — bosilganda tahrirlanadigan tugma ko'rinishida */
.quota-value {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 1px 5px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text);
  font-size: var(--font-size-base);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  transition: border-color var(--transition), color var(--transition), background-color var(--transition);
}

.quota-value :deep(svg) {
  opacity: 0.45;
}

.quota-value:hover {
  border-color: var(--color-accent);
  border-style: solid;
  background: var(--color-accent-soft-bg);
  color: var(--color-accent-soft-fg);
}

.quota-value:hover :deep(svg) {
  opacity: 1;
}

.quota-edit {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.quota-input {
  width: 5.5rem;
  height: 26px;
  text-align: right;
}

.icon-btn--ok:hover {
  color: var(--color-success-fg);
  background: var(--color-success-bg);
}

.foot-value {
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}
</style>
