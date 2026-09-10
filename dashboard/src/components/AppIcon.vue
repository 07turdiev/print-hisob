<script setup lang="ts">
/**
 * Ilovadagi yagona ikonka to'plami (feather uslubidagi chiziqli SVG'lar).
 * Har bir ikonka 24x24 katakda chiziladi va `currentColor` rangini oladi.
 */
const ICONS: Record<string, string> = {
  home: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/><path d="M9.5 20v-6h5v6"/>',
  quarterly:
    '<rect x="3" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.2"/>',
  monthly: '<rect x="3" y="4.5" width="18" height="16" rx="2"/><path d="M16 2.5v4M8 2.5v4M3 10h18"/>',
  employees:
    '<circle cx="9" cy="7.5" r="3.5"/><path d="M2.5 20.5v-1a5 5 0 0 1 5-5h3a5 5 0 0 1 5 5v1"/><path d="M16.5 4.2a3.5 3.5 0 0 1 0 6.6"/><path d="M20.5 20.5v-1a5 5 0 0 0-3-4.58"/>',
  printers:
    '<path d="M6 8.5V3h12v5.5"/><rect x="4.5" y="8.5" width="15" height="7" rx="1.5"/><rect x="7" y="13.5" width="10" height="7"/>',
  departments:
    '<rect x="2.5" y="7.5" width="19" height="13.5" rx="1.5"/><path d="M16 21V5.5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2V21"/>',
  journal:
    '<path d="M14.5 2.5h-8a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V8z"/><path d="M14.5 2.5V8h5.5"/><path d="M8.5 13h7M8.5 17h7"/>',
  agents:
    '<rect x="2.5" y="4" width="19" height="12.5" rx="1.5"/><path d="M8 20.5h8M12 16.5v4"/><circle cx="17.5" cy="8.5" r="1.1" fill="currentColor" stroke="none"/>',
  sun: '<circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8l1.8-1.8M18 6l1.8-1.8"/>',
  moon: '<path d="M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5 6.6 6.6 0 0 0 20.5 14.2z"/>',
  logout: '<path d="M9.5 20.5h-4a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2h4"/><path d="M16 16.5l4.5-4.5-4.5-4.5"/><path d="M20.5 12h-11.5"/>',
  'chevron-left': '<path d="M15 18l-6-6 6-6"/>',
  'chevron-right': '<path d="M9 18l6-6-6-6"/>',
  'chevron-down': '<path d="M6 9l6 6 6-6"/>',
  'chevron-up': '<path d="M18 15l-6-6-6 6"/>',
  menu: '<path d="M3.5 12h17M3.5 6h17M3.5 18h17"/>',
  search: '<circle cx="10.5" cy="10.5" r="7"/><path d="M20.5 20.5l-4.35-4.35"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.2 3.6-6.5 8-6.5s8 2.3 8 6.5"/>',
  warning:
    '<path d="M12 3.5 2.5 20.5h19z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.5" r="0.6" fill="currentColor" stroke="none"/>',
  refresh:
    '<path d="M4 12a8 8 0 0 1 14.3-4.9M20 12a8 8 0 0 1-14.3 4.9"/><path d="M18.5 3v4.5H14"/><path d="M5.5 21v-4.5H10"/>',
  download:
    '<path d="M12 3.5v11.5"/><path d="M7 10.5 12 15.5 17 10.5"/><path d="M4.5 17.5v2a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2"/>',
  document:
    '<path d="M7 2.5h7l4 4v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1z"/><path d="M14 2.5V7h4"/><path d="M8.5 12h7M8.5 15.5h7M8.5 8.5h2.5"/>',
  'check-circle': '<circle cx="12" cy="12" r="9"/><path d="M7.5 12.5l3 3 6-6.5"/>',
  check: '<path d="M5 12.5l5 5 9-10"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  layers: '<path d="M12 3 3 8l9 5 9-5-9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 16l9 5 9-5"/>',
  edit: '<path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17v3z"/><path d="M13.5 7.5l3 3"/>',
  filter: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
  chart: '<path d="M3.5 20.5h17"/><path d="M6.5 20.5V12M11 20.5V5.5M15.5 20.5v-6M20 20.5V9"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6.5V12l3.5 2.5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r="0.7" fill="currentColor" stroke="none"/>',
  shield: '<path d="M12 2.5 4.5 5.5v6c0 5 3.2 8.6 7.5 10 4.3-1.4 7.5-5 7.5-10v-6z"/><path d="M8.8 12l2.3 2.3 4.1-4.6"/>',
  pages:
    '<rect x="7" y="3" width="13" height="16" rx="1.5"/><path d="M16.5 21.5h-11a2 2 0 0 1-2-2V7"/><path d="M10.5 8h6M10.5 11.5h6"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
  'arrow-right': '<path d="M4.5 12h14"/><path d="M13 6.5 18.5 12 13 17.5"/>',
  building:
    '<path d="M4 21V4.5A1.5 1.5 0 0 1 5.5 3h8A1.5 1.5 0 0 1 15 4.5V21"/><path d="M15 10h3.5A1.5 1.5 0 0 1 20 11.5V21"/><path d="M2.5 21h19"/><path d="M7.5 7h4M7.5 11h4M7.5 15h4"/>',
}

const props = withDefaults(defineProps<{ name: string; size?: number }>(), { size: 18 })
</script>

<template>
  <svg
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="ICONS[props.name] ?? ''"
  />
</template>
