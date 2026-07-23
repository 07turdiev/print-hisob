import { defineStore } from 'pinia'
import type { PeriodType } from '../api/types'

const STORAGE_KEY = 'printerhisob.period'

function currentQuarter(month: number): number {
  return Math.floor((month - 1) / 3) + 1
}

const now = new Date()

interface PersistedPeriod {
  periodType: PeriodType
  year: number
  periodNo: number
}

function isValidYear(year: unknown): year is number {
  return typeof year === 'number' && Number.isInteger(year) && year >= 2000 && year <= 2100
}

function isValidPeriodNo(periodType: PeriodType, periodNo: unknown): periodNo is number {
  if (typeof periodNo !== 'number' || !Number.isInteger(periodNo)) return false
  return periodType === 'quarter' ? periodNo >= 1 && periodNo <= 4 : periodNo >= 1 && periodNo <= 12
}

/**
 * Restores the persisted period from localStorage, validating every field so a corrupt
 * or stale value (e.g. left over from before a periodType/periodNo range changed) can
 * never leave the store in an invalid state — it just falls back to the current period.
 */
function loadPersisted(): PersistedPeriod {
  const fallback: PersistedPeriod = {
    periodType: 'quarter',
    year: now.getFullYear(),
    periodNo: currentQuarter(now.getMonth() + 1),
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return fallback

    const parsed = JSON.parse(raw) as Partial<PersistedPeriod>
    const periodType: PeriodType = parsed.periodType === 'month' ? 'month' : 'quarter'
    const year = isValidYear(parsed.year) ? parsed.year : fallback.year
    const fallbackPeriodNo =
      periodType === 'quarter' ? currentQuarter(now.getMonth() + 1) : now.getMonth() + 1
    const periodNo = isValidPeriodNo(periodType, parsed.periodNo) ? parsed.periodNo : fallbackPeriodNo

    return { periodType, year, periodNo }
  } catch {
    return fallback
  }
}

function persistPeriod(period: PersistedPeriod) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(period))
  } catch {
    // localStorage unavailable (private mode etc.) — the period just won't survive a reload.
  }
}

const initial = loadPersisted()

export const usePeriodStore = defineStore('period', {
  state: () => ({
    periodType: initial.periodType,
    year: initial.year,
    periodNo: initial.periodNo,
    /** Filter shared by every panel on the page (client-side, applied to the employee table). */
    department: '' as string,
  }),
  actions: {
    /** Called when switching between the Quarterly and Monthly pages. */
    setPeriodType(periodType: PeriodType) {
      if (this.periodType === periodType) return
      this.periodType = periodType
      this.periodNo = periodType === 'quarter' ? currentQuarter(now.getMonth() + 1) : now.getMonth() + 1
      this.persist()
    },
    setYear(year: number) {
      this.year = year
      this.persist()
    },
    setPeriodNo(periodNo: number) {
      this.periodNo = periodNo
      this.persist()
    },
    setDepartment(department: string) {
      this.department = department
    },
    /** Persists periodType/year/periodNo so the selection survives a reload (per browser). */
    persist() {
      persistPeriod({ periodType: this.periodType, year: this.year, periodNo: this.periodNo })
    },
  },
})
