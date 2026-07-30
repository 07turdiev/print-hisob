/** Human-friendly relative time in Uzbek, shared by the Agentlar and AD sync indicators. */
export function formatRelativeMinutes(minutes: number | null): string {
  if (minutes === null || minutes < 1) return 'hozirgina'
  if (minutes < 60) return `${minutes} daqiqa oldin`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} soat oldin`
  const days = Math.floor(hours / 24)
  return `${days} kun oldin`
}
