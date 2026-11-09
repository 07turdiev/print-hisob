import { ref } from 'vue'
import { ApiError } from '../api/client'
import type { EmployeeStat, UserOverrideInput } from '../api/types'

/**
 * Bloklash va biriktirish tugmalarining umumiy mantig'i.
 *
 * Xodimlar sahifasida ham, Choraklik/Oylik hisobotlarda ham bir xil jadval
 * ishlatiladi, shuning uchun bu holat (qaysi qator band, qaysi xodim uchun
 * biriktirish oynasi ochiq, qanday xato chiqdi) bir joyda saqlanadi.
 */
export function useOverrideActions(
  save: (login: string, body: UserOverrideInput) => Promise<void>,
) {
  /** Ayni damda saqlanayotgan xodim — uning tugmalari o'chiriladi. */
  const busyLogin = ref<string | null>(null)
  /** Biriktirish oynasi ochilgan xodim (`null` — oyna yopiq). */
  const linkTarget = ref<EmployeeStat | null>(null)
  const actionError = ref<string | null>(null)

  async function run(login: string, body: UserOverrideInput): Promise<boolean> {
    busyLogin.value = login
    actionError.value = null
    try {
      await save(login, body)
      return true
    } catch (err) {
      // Server tushunarli sabab qaytaradi (masalan zanjir taqiqi) — aynan shuni
      // ko'rsatamiz, texnik xabarni emas.
      actionError.value =
        err instanceof ApiError
          ? (err.detail ?? "Amalni bajarib bo'lmadi")
          : "Amalni bajarib bo'lmadi"
      return false
    } finally {
      busyLogin.value = null
    }
  }

  async function toggleBlock(emp: EmployeeStat) {
    if (!emp.blocked) {
      const who = emp.fullName ?? emp.login
      // Bu odamning chop etishini to'xtatadi — tasodifan bosilmasligi uchun so'raymiz.
      if (!window.confirm(`${who} uchun chop etish bloklansinmi?`)) return
    }
    await run(emp.login, { blocked: !emp.blocked })
  }

  function startLink(emp: EmployeeStat) {
    actionError.value = null
    linkTarget.value = emp
  }

  function cancelLink() {
    linkTarget.value = null
    actionError.value = null
  }

  async function confirmLink(ownerLogin: string) {
    const target = linkTarget.value
    if (!target) return
    // Oyna faqat muvaffaqiyatda yopiladi — xato bo'lsa sabab o'sha yerda ko'rinadi.
    if (await run(target.login, { chargeToLogin: ownerLogin })) {
      linkTarget.value = null
    }
  }

  async function unlink(emp: EmployeeStat) {
    await run(emp.login, { chargeToLogin: null })
  }

  return {
    busyLogin,
    linkTarget,
    actionError,
    toggleBlock,
    startLink,
    cancelLink,
    confirmLink,
    unlink,
  }
}
