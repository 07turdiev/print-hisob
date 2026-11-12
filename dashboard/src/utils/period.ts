import type { PeriodType } from '../api/types'

export const MONTH_NAMES = [
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

/** Masalan "3-chorak" yoki "Iyul". */
export function periodLabel(periodType: PeriodType, periodNo: number): string {
  return periodType === 'quarter'
    ? `${periodNo}-chorak`
    : MONTH_NAMES[periodNo - 1] ?? String(periodNo)
}

function isoDate(year: number, monthIndex: number): string {
  // `Date.UTC` oy oshib ketganini o'zi keyingi yilga o'tkazadi (13-oy -> yanvar).
  return new Date(Date.UTC(year, monthIndex, 1)).toISOString().slice(0, 10)
}

/**
 * Davrning sanalari jurnal filtri uchun: `since` kiradi, `until` kirmaydi.
 * Masalan 4-chorak 2026 -> `2026-10-01` .. `2027-01-01`.
 */
export function periodDateRange(
  periodType: PeriodType,
  year: number,
  periodNo: number,
): { since: string; until: string } {
  const firstMonth = periodType === 'quarter' ? (periodNo - 1) * 3 : periodNo - 1
  const months = periodType === 'quarter' ? 3 : 1
  return { since: isoDate(year, firstMonth), until: isoDate(year, firstMonth + months) }
}
