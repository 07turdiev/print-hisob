<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EmployeeStat } from '../api/types'
import { usePeriodStore } from '../stores/period'
import { periodLabel as formatPeriodLabel } from '../utils/period'
import AppIcon from './AppIcon.vue'
import EmployeePrintersDialog from './EmployeePrintersDialog.vue'
import StatusBadge from './StatusBadge.vue'
import UsageBar from './UsageBar.vue'


const props = withDefaults(
  defineProps<{
    employees: EmployeeStat[]
    title?: string
    busyLogin?: string | null
    /**
     * Jadval ikki vazifada ishlatiladi va ustunlari shunga qarab farq qiladi:
     *
     * - `management` (Xodimlar va normalar) — norma belgilash, bloklash, biriktirish.
     *   Sarf raqamlari ko'rsatilmaydi: bu sahifa boshqaruv uchun, hisobot uchun emas.
     * - `report` (Choraklik/Oylik) — faqat raqamlar, amal tugmalarisiz.
     */
    variant?: 'management' | 'report'
  }>(),
  { title: "Xodimlar bo'yicha norma", busyLogin: null, variant: 'report' },
)

const isManagement = computed(() => props.variant === 'management')
const emit = defineEmits<{
  save: [login: string, allocatedPages: number]
  'toggle-block': [employee: EmployeeStat]
  link: [employee: EmployeeStat]
  unlink: [employee: EmployeeStat]
}>()

const periodStore = usePeriodStore()
const numberFormat = new Intl.NumberFormat('uz-UZ')
const fmt = (n: number) => numberFormat.format(n)

/** Masalan "3-chorak" yoki "Iyul" — kvota har davr uchun alohida saqlanadi. */
const periodLabel = computed(() => formatPeriodLabel(periodStore.periodType, periodStore.periodNo))

/** Ismi bosilgan xodim: uning printerlari oynada ko'rsatiladi. */
const printersOf = ref<EmployeeStat | null>(null)

const quotaColumnLabel = computed(() => `Norma (${periodLabel.value})`)

type SortKey =
  | 'name'
  | 'department'
  | 'used'
  | 'linked'
  | 'total'
  | 'allocated'
  | 'remaining'
  | 'percent'

// Boshqaruv ko'rinishida sarf ustunlari yo'q, shuning uchun standart saralash ism bo'yicha.
const sortKey = ref<SortKey>(props.variant === 'management' ? 'name' : 'total')
const sortDesc = ref(props.variant !== 'management')

function percentOf(emp: EmployeeStat): number {
  if (emp.allocated > 0) return (emp.usedTotal / emp.allocated) * 100
  return emp.usedTotal > 0 ? Infinity : 0
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
      case 'department':
        return dir * (a.department ?? '').localeCompare(b.department ?? '')
      case 'used':
        return dir * (a.used - b.used)
      case 'linked':
        return dir * (a.usedFromLinked - b.usedFromLinked)
      case 'allocated':
        return dir * (a.allocated - b.allocated)
      case 'remaining':
        return dir * (a.remaining - b.remaining)
      case 'percent':
        return dir * (percentOf(a) - percentOf(b))
      case 'total':
      default:
        return dir * (a.usedTotal - b.usedTotal)
    }
  })
  return list
})

/** Jadval ostidagi jamlanma.
 *
 *  "Jami sarflangan" — har kimning **o'z** sarfi yig'indisi. `usedTotal` ni
 *  qo'shib bo'lmaydi: biriktirilgan varaqlar ikki qatorda (o'zinikida va
 *  egasining "biriktirilgandan" ustunida) ko'ringani uchun qo'sh hisob chiqadi.
 */
const totals = computed(() => ({
  used: props.employees.reduce((sum, e) => sum + e.used, 0),
  allocated: props.employees.reduce((sum, e) => sum + e.allocated, 0),
  overLimit: props.employees.filter((e) => e.overLimit).length,
  blocked: props.employees.filter((e) => e.blocked).length,
  linked: props.employees.filter((e) => e.chargedTo).length,
}))

/** Bo'sh jadval xabari uchun ustunlar soni. */
const columnCount = computed(() => (isManagement.value ? 6 : 10))

const editingLogin = ref<string | null>(null)
const editValue = ref(0)

function startEdit(emp: EmployeeStat) {
  editingLogin.value = emp.login
  editValue.value = emp.allocated
}

function cancelEdit() {
  editingLogin.value = null
}

function confirmEdit(login: string) {
  emit('save', login, editValue.value)
  editingLogin.value = null
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
            <th class="sortable" @click="setSort('department')">
              Bo'lim <span class="sort-caret">{{ sortCaret('department') }}</span>
            </th>
            <th>Holat</th>
            <th v-if="!isManagement" class="sortable num" title="Xodimning o'z sarfi" @click="setSort('used')">
              O'zi <span class="sort-caret">{{ sortCaret('used') }}</span>
            </th>
            <th
              v-if="!isManagement"
              class="sortable num"
              title="Unga biriktirilgan xodimlardan qo'shilgan varaqlar"
              @click="setSort('linked')"
            >
              Biriktirilgandan <span class="sort-caret">{{ sortCaret('linked') }}</span>
            </th>
            <th v-if="!isManagement" class="sortable num" title="O'zi + biriktirilgandan" @click="setSort('total')">
              Jami <span class="sort-caret">{{ sortCaret('total') }}</span>
            </th>
            <th class="sortable num" @click="setSort('allocated')">
              {{ quotaColumnLabel }} <span class="sort-caret">{{ sortCaret('allocated') }}</span>
            </th>
            <th v-if="!isManagement" class="sortable num" @click="setSort('remaining')">
              Qoldiq <span class="sort-caret">{{ sortCaret('remaining') }}</span>
            </th>
            <th v-if="!isManagement" class="sortable col-usage" @click="setSort('percent')">
              Bajarilishi <span class="sort-caret">{{ sortCaret('percent') }}</span>
            </th>
            <th v-if="isManagement" class="col-actions">Amallar</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="(emp, i) in sortedEmployees"
            :key="emp.login"
            :class="{ 'row-danger': emp.blocked, 'row-warning': !isManagement && !emp.blocked && emp.overLimit }"
          >
            <td class="col-num">{{ i + 1 }}</td>

            <td>
              <button
                type="button"
                class="name-link"
                title="Qaysi printerlardan chop etganini ko'rish"
                @click="printersOf = emp"
              >
                {{ emp.fullName ?? emp.login }}
              </button>
              <div class="muted">{{ emp.login }}<template v-if="emp.position"> · {{ emp.position }}</template></div>
              <!-- Biriktirilgan xodim: varaqlari kimning hisobida ko'rinishi -->
              <div v-if="emp.chargedTo" class="linked-note">
                <AppIcon name="link" :size="11" />
                {{ emp.chargedTo }} hisobiga qo'shiladi
              </div>
            </td>

            <td>{{ emp.department ?? '—' }}</td>

            <td>
              <div class="status-cell">
                <StatusBadge :status="emp.matchStatus" />
                <span v-if="emp.blocked" class="badge badge--danger" title="Chop etish bloklangan">
                  Bloklangan
                </span>
                <span
                  v-else-if="emp.accessGroup"
                  class="badge badge--accent"
                  :title="`Printer ruxsati guruhi: ${emp.accessGroup}`"
                >
                  Istisno
                </span>
              </div>
            </td>

            <td v-if="!isManagement" class="num">{{ fmt(emp.used) }}</td>

            <td v-if="!isManagement" class="num">
              <span v-if="emp.usedFromLinked > 0" class="linked-value" title="Biriktirilgan xodimlardan">
                +{{ fmt(emp.usedFromLinked) }}
              </span>
              <span v-else class="muted">—</span>
            </td>

            <td v-if="!isManagement" class="num strong">{{ fmt(emp.usedTotal) }}</td>

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
                <button type="button" class="icon-btn icon-btn--ok" title="Saqlash" @click="confirmEdit(emp.login)">
                  <AppIcon name="check" :size="15" />
                </button>
                <button type="button" class="icon-btn" title="Bekor qilish" @click="cancelEdit">
                  <AppIcon name="close" :size="15" />
                </button>
              </div>

              <button v-else type="button" class="quota-value" title="Normani o'zgartirish" @click="startEdit(emp)">
                {{ fmt(emp.allocated) }}
                <AppIcon name="edit" :size="13" />
              </button>
            </td>

            <td v-if="!isManagement" class="num" :class="{ negative: emp.remaining < 0 }">
              {{ fmt(emp.remaining) }}
            </td>

            <td v-if="!isManagement" class="col-usage">
              <UsageBar :used="emp.usedTotal" :allocated="emp.allocated" :over-limit="emp.overLimit" />
            </td>

            <td v-if="isManagement" class="col-actions">
              <div class="actions">
                <button
                  type="button"
                  class="icon-btn"
                  :class="emp.blocked ? 'icon-btn--ok' : 'icon-btn--danger'"
                  :disabled="busyLogin === emp.login"
                  :title="emp.blocked ? 'Blokdan chiqarish' : 'Chop etishni bloklash'"
                  @click="emit('toggle-block', emp)"
                >
                  <AppIcon :name="emp.blocked ? 'unlock' : 'lock'" :size="15" />
                </button>

                <button
                  v-if="emp.chargedTo"
                  type="button"
                  class="icon-btn"
                  :disabled="busyLogin === emp.login"
                  :title="`Biriktirishni bekor qilish (${emp.chargedTo})`"
                  @click="emit('unlink', emp)"
                >
                  <AppIcon name="unlink" :size="15" />
                </button>
                <button
                  v-else
                  type="button"
                  class="icon-btn"
                  :disabled="busyLogin === emp.login"
                  title="Boshqa xodimga biriktirish"
                  @click="emit('link', emp)"
                >
                  <AppIcon name="link" :size="15" />
                </button>
              </div>
            </td>
          </tr>

          <tr v-if="!sortedEmployees.length">
            <td :colspan="columnCount" class="empty">Ushbu davr uchun ma'lumot topilmadi</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="employees.length" class="panel__foot">
      <!-- Boshqaruv ko'rinishida sarf raqamlari yo'q, shuning uchun jamlanma ham boshqacha -->
      <span v-if="isManagement">
        Jami norma: <strong class="foot-value">{{ fmt(totals.allocated) }}</strong> varaq
      </span>
      <span v-else>
        <span title="Biriktirilgan varaqlar ikki marta qo'shilmagan">Haqiqiy qog'oz sarfi:</span>
        <strong class="foot-value">{{ fmt(totals.used) }}</strong> varaq &nbsp;·&nbsp;
        Jami norma: <strong class="foot-value">{{ fmt(totals.allocated) }}</strong> varaq
      </span>

      <span class="foot-badges">
        <span v-if="totals.blocked" class="badge badge--danger">
          Bloklangan: {{ totals.blocked }} ta
        </span>
        <template v-if="isManagement">
          <span v-if="totals.linked" class="badge badge--accent">
            Biriktirilgan: {{ totals.linked }} ta
          </span>
          <span v-if="!totals.blocked && !totals.linked" class="badge badge--muted badge--plain">
            Bloklangan yoki biriktirilgan xodim yo'q
          </span>
        </template>
        <template v-else>
          <span v-if="totals.overLimit" class="badge badge--warning">
            Normadan oshgan: {{ totals.overLimit }} ta
          </span>
          <span v-if="!totals.blocked && !totals.overLimit" class="badge badge--success">
            Normadan oshgan xodim yo'q
          </span>
        </template>
      </span>
    </footer>

    <EmployeePrintersDialog v-if="printersOf" :employee="printersOf" @close="printersOf = null" />
  </section>
</template>

<style scoped>
.col-usage {
  width: 10rem;
}

.col-actions {
  width: 5.5rem;
  text-align: center;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

/* Xodim ismi: bosilganda printerlari oynasi ochiladi */
.name-link {
  display: block;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.name-link:hover,
.name-link:focus-visible {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* Biriktirilgan xodim qatoridagi eslatma */
.linked-note {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--color-accent);
}

/* Egasining qatoridagi "+85" ko'rinishidagi qo'shimcha */
.linked-value {
  color: var(--color-accent);
  font-weight: 600;
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
  width: 5rem;
  height: 26px;
  text-align: right;
}

.icon-btn--ok:hover:not(:disabled) {
  color: var(--color-success-fg);
  background: var(--color-success-bg);
}

.icon-btn--danger:hover:not(:disabled) {
  color: var(--color-danger-fg);
  background: var(--color-danger-bg);
}

.icon-btn:disabled {
  opacity: 0.45;
  cursor: default;
}

.foot-badges {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.foot-value {
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}
</style>
