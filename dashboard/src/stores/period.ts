import { defineStore } from 'pinia'
import type { PeriodType } from '../api/types'

function currentQuarter(month: number): number {
  return Math.floor((month - 1) / 3) + 1
}

const now = new Date()

export const usePeriodStore = defineStore('period', {
  state: () => ({
    periodType: 'quarter' as PeriodType,
    year: now.getFullYear(),
    periodNo: currentQuarter(now.getMonth() + 1),
    /** Filter shared by every panel on the page (client-side, applied to the employee table). */
    department: '' as string,
  }),
  actions: {
    /** Called when switching between the Quarterly and Monthly pages. */
    setPeriodType(periodType: PeriodType) {
      if (this.periodType === periodType) return
      this.periodType = periodType
      this.periodNo = periodType === 'quarter' ? currentQuarter(now.getMonth() + 1) : now.getMonth() + 1
    },
    setYear(year: number) {
      this.year = year
    },
    setPeriodNo(periodNo: number) {
      this.periodNo = periodNo
    },
    setDepartment(department: string) {
      this.department = department
    },
  },
})
