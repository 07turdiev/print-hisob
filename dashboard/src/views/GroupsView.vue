<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { PrinterGroup, PrinterGroupPolicy } from '../api/types'
import { usePrinterGroupsPage } from '../composables/usePrinterGroupsPage'
import { usePolicyViolations } from '../composables/usePolicyViolations'
import AppIcon from '../components/AppIcon.vue'
import PickerList from '../components/PickerList.vue'

const {
  groups,
  printers,
  employees,
  employeeByLogin,
  takenLogins,
  loading,
  error,
  savingId,
  rowErrors,
  creating,
  createError,
  access,
  savingAccess,
  accessError,
  saveAccess,
  create,
  save,
  remove,
} = usePrinterGroupsPage()

const POLICIES: { value: PrinterGroupPolicy; label: string; hint: string }[] = [
  { value: 'all', label: 'Barcha printerlar', hint: 'Istisno: istalgan printerdan chop etadi' },
  {
    value: 'allowed',
    label: "Ma'lum printerlar",
    hint: 'Istisno: umumiy printerlar va quyida belgilanganlardan chop etadi',
  },
]

function policyLabel(policy: PrinterGroupPolicy): string {
  return POLICIES.find((p) => p.value === policy)?.label ?? policy
}

function sameList(a: readonly (string | number)[], b: readonly (string | number)[]): boolean {
  return a.length === b.length && [...a].sort().join('|') === [...b].sort().join('|')
}

// --- Standart qoida ---
const draftPublic = ref<(string | number)[]>([])
const draftRestrict = ref(false)

watch(
  access,
  (current) => {
    draftPublic.value = [...current.publicDeviceIds]
    draftRestrict.value = current.restrictDefault
  },
  { immediate: true },
)

const accessDirty = computed(
  () =>
    draftRestrict.value !== access.value.restrictDefault ||
    !sameList(draftPublic.value, access.value.publicDeviceIds),
)

/** Umumiy printersiz cheklov hammani to'xtatib qo'ygan bo'lardi. */
const accessInvalid = computed(() => draftRestrict.value && draftPublic.value.length === 0)

async function submitAccess() {
  try {
    await saveAccess({
      restrictDefault: draftRestrict.value,
      publicDeviceIds: draftPublic.value.map(Number),
    })
    // Umumiy ro'yxat o'zgarsa, hisobotdagi buzilishlar ham o'zgaradi.
    reloadViolations()
  } catch {
    // Xato panel ichida ko'rsatiladi.
  }
}

// --- Yangi guruh ---
const newName = ref('')
const newPolicy = ref<PrinterGroupPolicy>('all')

async function submitNew() {
  const name = newName.value.trim()
  if (!name) return
  try {
    const made = await create(name, newPolicy.value)
    newName.value = ''
    newPolicy.value = 'all'
    openId.value = made.id
  } catch {
    // Xato forma ostida ko'rsatiladi.
  }
}

// --- Tahrirlash ---
/** Qaysi guruh ochilgan (bir vaqtda bittasi). */
const openId = ref<number | null>(null)
const draftName = ref('')
const draftPolicy = ref<PrinterGroupPolicy>('all')
const draftDevices = ref<(string | number)[]>([])
const draftLogins = ref<(string | number)[]>([])

function toggleOpen(group: PrinterGroup) {
  if (openId.value === group.id) {
    openId.value = null
    return
  }
  openId.value = group.id
  draftName.value = group.name
  draftPolicy.value = group.policy
  draftDevices.value = [...group.deviceIds]
  draftLogins.value = [...group.logins]
}

const openGroup = computed(() => groups.value.find((g) => g.id === openId.value) ?? null)

/** Boshqa guruh egallagan xodimlar ro'yxatdan chiqariladi — bir xodim bitta guruhda. */
const pickableEmployees = computed(() => {
  const taken = takenLogins(openId.value ?? -1)
  return employees.value.filter((e) => !taken.has(e.login.toLowerCase()))
})

const dirty = computed(() => {
  const g = openGroup.value
  if (!g) return false
  return (
    draftName.value.trim() !== g.name ||
    draftPolicy.value !== g.policy ||
    !sameList(draftDevices.value, g.deviceIds) ||
    !sameList(draftLogins.value, g.logins)
  )
})

/** `allowed` tanlangan, lekin na umumiy, na qo'shimcha printer bor — bu a'zolarni to'sadi. */
const emptyAllowed = computed(
  () =>
    draftPolicy.value === 'allowed' &&
    draftDevices.value.length === 0 &&
    access.value.publicDeviceIds.length === 0,
)

async function submitEdit() {
  const g = openGroup.value
  if (!g) return
  try {
    await save(g.id, {
      name: draftName.value.trim(),
      policy: draftPolicy.value,
      deviceIds: draftDevices.value.map(Number),
      logins: draftLogins.value.map(String),
    })
    openId.value = null
  } catch {
    // Xato guruh ostida ko'rsatiladi.
  }
}

const confirmDeleteId = ref<number | null>(null)

async function confirmRemove(id: number) {
  try {
    await remove(id)
    confirmDeleteId.value = null
    if (openId.value === id) openId.value = null
  } catch {
    confirmDeleteId.value = null
  }
}

function memberLabel(login: string): string {
  return employeeByLogin.value.get(login.toLowerCase())?.fullName ?? login
}

// --- Buzilishlar hisoboti ---
const {
  rows: violations,
  totalPages: violationPages,
  peopleCount: violationPeople,
  loading: violationsLoading,
  error: violationsError,
  reload: reloadViolations,
} = usePolicyViolations()

const numberFormat = new Intl.NumberFormat('uz-UZ')
const fmt = (n: number) => numberFormat.format(n)

const dateFormat = new Intl.DateTimeFormat('uz-UZ', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function when(iso: string): string {
  return dateFormat.format(new Date(iso))
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
        Guruhga kirmagan xodim standart qoidaga bo'ysunadi: cheklov yoqilgan bo'lsa faqat umumiy
        printerlardan chop etadi. Guruh shu qoidadan istisno. Bir xodim bir vaqtda faqat bitta
        guruhda bo'ladi. Umuman chop eta olmaydigan xodim "Xodimlar va normalar" sahifasida
        bloklanadi.
      </span>
    </p>

    <p class="alert alert--warning">
      <span class="alert__icon"><AppIcon name="clock" :size="16" /></span>
      <span>
        Printer ro'yxati bo'yicha cheklov agent yangilanganidan keyin kuchga kiradi, hozircha u
        faqat hisobotda ko'rinadi.
      </span>
    </p>

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="shield" :size="16" /></span>
          Umumiy printerlar
        </h2>
        <span class="panel__count">
          {{ access.publicDeviceIds.length }} ta printer ·
          {{ access.restrictDefault ? 'cheklov yoqilgan' : "cheklov o'chiq" }}
        </span>
      </header>

      <div class="editor editor--flat">
        <div class="field">
          <span class="field__label">Barcha xodimlar chop eta oladigan printerlar</span>
          <PickerList
            :items="printers"
            :key-of="(p) => p.id"
            :label="(p) => p.displayName"
            :sublabel="(p) => p.lastIp"
            :selected="draftPublic"
            :disabled="savingAccess"
            placeholder="Printer nomi bo'yicha qidirish"
            empty-text="Reyestrda printer yo'q"
            @update:selected="draftPublic = $event"
          />
          <p class="field__hint">
            Microsoft Print to PDF kabi virtual printerlarni ham shu yerda belgilang, aks holda
            PDF'ga saqlash ham bloklanadi.
          </p>
        </div>

        <label class="radio">
          <input v-model="draftRestrict" type="checkbox" :disabled="savingAccess" />
          <span>
            <span class="radio__label">Boshqa printerlarni cheklash</span>
            <span class="radio__hint">
              Guruhga kirmagan xodim faqat yuqoridagi printerlardan chop etadi. O'chirilsa hamma
              avvalgidek ishlaydi.
            </span>
          </span>
        </label>

        <p v-if="accessInvalid" class="row-error">
          Avval umumiy printerlarni belgilang, aks holda hech kim chop eta olmaydi.
        </p>
        <p v-if="accessError" class="row-error">{{ accessError }}</p>

        <div class="editor__actions">
          <button
            type="button"
            class="btn btn--primary"
            :disabled="!accessDirty || accessInvalid || savingAccess"
            @click="submitAccess"
          >
            Saqlash
          </button>
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="shield" :size="16" /></span>
          Yangi istisno guruhi
        </h2>
      </header>

      <form class="create" @submit.prevent="submitNew">
        <input
          v-model="newName"
          type="text"
          class="create__name"
          placeholder="Guruh nomi — masalan: Vazir o'rinbosarlari"
          :disabled="creating"
        />
        <select v-model="newPolicy" class="create__policy" :disabled="creating">
          <option v-for="p in POLICIES" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
        <button type="submit" class="btn btn--primary" :disabled="creating || !newName.trim()">
          Qo'shish
        </button>
      </form>

      <p v-if="createError" class="row-error create__error">{{ createError }}</p>
    </section>

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="layers" :size="16" /></span>
          Guruhlar
        </h2>
        <span class="panel__count">{{ groups.length }} ta guruh</span>
      </header>

      <div v-if="!groups.length && !loading" class="empty-block">
        Hali guruh tuzilmagan. Yuqoridagi forma orqali qo'shing.
      </div>

      <ul v-else class="groups">
        <li v-for="g in groups" :key="g.id" class="group">
          <div class="group__row">
            <button type="button" class="group__main" @click="toggleOpen(g)">
              <AppIcon
                :name="openId === g.id ? 'chevron-down' : 'chevron-right'"
                :size="15"
                class="group__caret"
              />
              <span class="group__name">{{ g.name }}</span>
              <span class="badge" :class="`badge--${g.policy}`">{{ policyLabel(g.policy) }}</span>
              <span class="group__meta">
                {{ g.logins.length }} xodim
                <template v-if="g.policy === 'allowed'">
                  · {{ g.deviceIds.length }} printer
                </template>
              </span>
            </button>

            <div class="group__actions">
              <template v-if="confirmDeleteId === g.id">
                <span class="confirm">O'chirilsinmi?</span>
                <button
                  type="button"
                  class="icon-btn icon-btn--danger"
                  title="Ha, o'chirish"
                  :disabled="savingId === g.id"
                  @click="confirmRemove(g.id)"
                >
                  <AppIcon name="check" :size="15" />
                </button>
                <button
                  type="button"
                  class="icon-btn"
                  title="Bekor qilish"
                  @click="confirmDeleteId = null"
                >
                  <AppIcon name="close" :size="15" />
                </button>
              </template>
              <button
                v-else
                type="button"
                class="icon-btn"
                title="Guruhni o'chirish"
                :disabled="savingId === g.id"
                @click="confirmDeleteId = g.id"
              >
                <AppIcon name="close" :size="15" />
              </button>
            </div>
          </div>

          <p v-if="rowErrors[g.id]" class="row-error">{{ rowErrors[g.id] }}</p>

          <div v-if="openId === g.id" class="editor">
            <label class="field">
              <span class="field__label">Nomi</span>
              <input v-model="draftName" type="text" :disabled="savingId === g.id" />
            </label>

            <fieldset class="field">
              <legend class="field__label">Printer ruxsati</legend>
              <label v-for="p in POLICIES" :key="p.value" class="radio">
                <input
                  v-model="draftPolicy"
                  type="radio"
                  :value="p.value"
                  :disabled="savingId === g.id"
                />
                <span>
                  <span class="radio__label">{{ p.label }}</span>
                  <span class="radio__hint">{{ p.hint }}</span>
                </span>
              </label>
            </fieldset>

            <div v-if="draftPolicy === 'allowed'" class="field">
              <span class="field__label">Umumiy printerlarga qo'shimcha ruxsat</span>
              <p v-if="emptyAllowed" class="row-error">
                Birorta printer belgilanmagan — bu holatda guruh a'zolari hech qaysi printerdan
                chop eta olmaydi.
              </p>
              <PickerList
                :items="printers"
                :key-of="(p) => p.id"
                :label="(p) => p.displayName"
                :sublabel="(p) => p.lastIp"
                :selected="draftDevices"
                :disabled="savingId === g.id"
                placeholder="Printer nomi bo'yicha qidirish"
                empty-text="Reyestrda printer yo'q"
                @update:selected="draftDevices = $event"
              />
            </div>

            <div class="field">
              <span class="field__label">Guruh a'zolari</span>
              <PickerList
                :items="pickableEmployees"
                :key-of="(e) => e.login"
                :label="(e) => e.fullName ?? e.login"
                :sublabel="(e) => e.department"
                :selected="draftLogins"
                :disabled="savingId === g.id"
                placeholder="Xodim ismi bo'yicha qidirish"
                empty-text="Tanlash uchun xodim qolmadi"
                @update:selected="draftLogins = $event"
              />
              <p class="field__hint">
                Boshqa guruhdagi xodimlar ro'yxatda ko'rinmaydi — avval ularni o'sha guruhdan
                chiqaring.
              </p>
            </div>

            <div v-if="g.logins.length" class="members">
              <span class="field__label">Hozirgi a'zolar</span>
              <div class="members__list">
                <span v-for="login in g.logins" :key="login" class="chip">
                  {{ memberLabel(login) }}
                </span>
              </div>
            </div>

            <div class="editor__actions">
              <button
                type="button"
                class="btn btn--primary"
                :disabled="!dirty || savingId === g.id || !draftName.trim()"
                @click="submitEdit"
              >
                Saqlash
              </button>
              <button type="button" class="btn" @click="openId = null">Bekor qilish</button>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <section class="panel">
      <header class="panel__head">
        <h2 class="panel__title">
          <span class="panel__title-icon"><AppIcon name="warning" :size="16" /></span>
          Ruxsat etilmagan printerdan chop etilgan
        </h2>
        <span class="panel__count">
          <template v-if="violations.length">
            {{ violationPeople }} xodim · {{ fmt(violationPages) }} varaq
          </template>
          <template v-else>toza</template>
        </span>
      </header>

      <p v-if="violationsError" class="alert alert--danger panel__alert">
        <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
        <span>{{ violationsError }}</span>
        <button type="button" class="btn" @click="reloadViolations">Qayta urinish</button>
      </p>

      <div v-else-if="!violations.length && !violationsLoading" class="empty-block">
        Tanlangan davrda ruxsat etilmagan printerdan chop etilmagan.
      </div>

      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Xodim</th>
              <th>Guruh</th>
              <th>Printer</th>
              <th class="num">Varaqlar</th>
              <th class="num">Ishlar</th>
              <th>So'nggi</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(v, i) in violations" :key="`${v.login}-${v.deviceId}-${i}`">
              <td>
                <div class="strong">{{ v.fullName ?? v.login }}</div>
                <div class="muted small">{{ v.department ?? v.login }}</div>
              </td>
              <td>
                <span class="badge" :class="`badge--${v.policy}`">{{ v.groupName }}</span>
              </td>
              <td>{{ v.printerName }}</td>
              <td class="num strong negative">{{ fmt(v.pages) }}</td>
              <td class="num">{{ fmt(v.jobs) }}</td>
              <td class="small">{{ when(v.lastAt) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p v-if="loading || violationsLoading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>

<style scoped>
.create {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  flex-wrap: wrap;
}

.create__name {
  flex: 1 1 16rem;
}

.create__policy {
  flex: 0 0 11rem;
}

.create__error {
  padding: 0 var(--space-4) var(--space-3);
}

.empty-block {
  padding: var(--space-5) var(--space-4);
  color: var(--color-text-muted);
  text-align: center;
  font-size: var(--font-size-sm);
}

.groups {
  list-style: none;
  margin: 0;
  padding: 0;
}

.group + .group {
  border-top: 1px solid var(--color-border);
}

.group__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 2px var(--space-4) 2px var(--space-2);
}

.group__main {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1 1 auto;
  min-width: 0;
  padding: 8px var(--space-2);
  border: none;
  background: transparent;
  color: var(--color-text);
  text-align: left;
}

.group__caret {
  flex-shrink: 0;
  color: var(--color-text-muted);
}

.group__name {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group__meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  white-space: nowrap;
}

.group__actions {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}

.confirm {
  color: var(--color-danger-fg);
  font-size: var(--font-size-xs);
}

.badge {
  flex-shrink: 0;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.badge--all {
  background: var(--color-success-bg);
  color: var(--color-success-fg);
}

.badge--allowed {
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
}

.badge--default {
  background: var(--color-surface-2);
  color: var(--color-text-muted);
}

.editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4) var(--space-4);
  border-top: 1px dashed var(--color-border);
  background: var(--color-surface-2);
}

.editor--flat {
  border-top: none;
  background: transparent;
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  border: none;
  margin: 0;
  padding: 0;
  min-width: 0;
}

.field__label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 0;
}

.field__hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.radio {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  cursor: pointer;
}

.radio__label {
  display: block;
  font-size: var(--font-size-sm);
}

.radio__hint {
  display: block;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.members__list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.chip {
  padding: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  font-size: var(--font-size-xs);
}

.editor__actions {
  display: flex;
  gap: var(--space-2);
}

.row-error {
  color: var(--color-danger-fg);
  font-size: var(--font-size-xs);
}

.small {
  font-size: var(--font-size-xs);
}

.panel__alert {
  margin: var(--space-3) var(--space-4);
}

.icon-btn--danger:hover:not(:disabled) {
  color: var(--color-danger-fg);
  background: var(--color-danger-bg);
}

.icon-btn:disabled {
  opacity: 0.45;
  cursor: default;
}
</style>
