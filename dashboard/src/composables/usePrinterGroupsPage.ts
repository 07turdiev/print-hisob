import { computed, reactive, ref } from 'vue'
import {
  ApiError,
  createPrinterGroup,
  deletePrinterGroup,
  getEmployees,
  getPrinters,
  getPrinterGroups,
  updatePrinterGroup,
} from '../api/client'
import type {
  Employee,
  Printer,
  PrinterGroup,
  PrinterGroupPatch,
  PrinterGroupPolicy,
} from '../api/types'

/**
 * Guruhlar sahifasi.
 *
 * Uchta ro'yxat birga kerak bo'ladi: guruhlar, reyestrdagi printerlar (ruxsat
 * belgilash uchun) va AD xodimlari (a'zo tanlash uchun). Ularning ikkitasi
 * o'zgarmaydigan ma'lumotnoma, shuning uchun bir marta yuklanadi.
 */
export function usePrinterGroupsPage() {
  const groups = ref<PrinterGroup[]>([])
  const printers = ref<Printer[]>([])
  const employees = ref<Employee[]>([])

  const loading = ref(false)
  const error = ref<string | null>(null)

  /** Qaysi guruh saqlanmoqda va unda qanday xato bo'lgani. */
  const savingId = ref<number | null>(null)
  const rowErrors = reactive<Record<number, string>>({})
  const creating = ref(false)
  const createError = ref<string | null>(null)

  function describe(err: unknown, fallback: string): string {
    if (err instanceof ApiError) return err.detail ?? err.message
    return fallback
  }

  async function reload() {
    loading.value = true
    error.value = null
    try {
      const [g, p, e] = await Promise.all([
        getPrinterGroups(),
        getPrinters(),
        // Guruhga faqat ishlayotgan xodimlar qo'shiladi.
        getEmployees({ isActive: true, limit: 2000 }),
      ])
      groups.value = g
      printers.value = p
      employees.value = e
    } catch (err) {
      error.value = describe(err, "Ma'lumotlarni yuklab bo'lmadi")
    } finally {
      loading.value = false
    }
  }

  reload()

  /** `login` -> xodim, guruh a'zolarini ism bilan ko'rsatish uchun. */
  const employeeByLogin = computed(() => {
    const map = new Map<string, Employee>()
    for (const e of employees.value) map.set(e.login.toLowerCase(), e)
    return map
  })

  /** Boshqa guruhlar egallab turgan loginlar — bir xodim faqat bitta guruhda. */
  function takenLogins(exceptGroupId: number): Set<string> {
    const taken = new Set<string>()
    for (const g of groups.value) {
      if (g.id === exceptGroupId) continue
      for (const login of g.logins) taken.add(login)
    }
    return taken
  }

  async function create(name: string, policy: PrinterGroupPolicy) {
    creating.value = true
    createError.value = null
    try {
      const made = await createPrinterGroup(name, policy)
      groups.value = [...groups.value, made].sort((a, b) => a.name.localeCompare(b.name))
      return made
    } catch (err) {
      createError.value = describe(err, "Guruh yaratib bo'lmadi")
      throw err
    } finally {
      creating.value = false
    }
  }

  async function save(id: number, patch: PrinterGroupPatch) {
    savingId.value = id
    delete rowErrors[id]
    try {
      const updated = await updatePrinterGroup(id, patch)
      groups.value = groups.value
        .map((g) => (g.id === id ? updated : g))
        .sort((a, b) => a.name.localeCompare(b.name))
      return updated
    } catch (err) {
      rowErrors[id] = describe(err, "Saqlab bo'lmadi")
      throw err
    } finally {
      savingId.value = null
    }
  }

  async function remove(id: number) {
    savingId.value = id
    delete rowErrors[id]
    try {
      await deletePrinterGroup(id)
      groups.value = groups.value.filter((g) => g.id !== id)
    } catch (err) {
      rowErrors[id] = describe(err, "Guruhni o'chirib bo'lmadi")
      throw err
    } finally {
      savingId.value = null
    }
  }

  return {
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
    create,
    save,
    remove,
    reload,
  }
}
