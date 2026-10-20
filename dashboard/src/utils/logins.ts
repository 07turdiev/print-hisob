/**
 * Login normallashtirish — backenddagi `app/logins.py: normalize_login` bilan
 * bir xil qoida: `DOMAIN\` prefiksi olib tashlanadi va kichik harfga o'tkaziladi.
 *
 * Kerak, chunki chop etish yozuvlaridagi login AD'dagi yozilishdan registr yoki
 * domen prefiksi bilan farq qilishi mumkin, taqqoslash esa bir xil bo'lishi shart.
 */
export function normalizeLogin(raw: string | null | undefined): string {
  if (!raw) return ''
  const value = raw.trim()
  const slash = value.lastIndexOf('\\')
  return (slash >= 0 ? value.slice(slash + 1) : value).toLowerCase()
}
