<script setup lang="ts">
/** Small inline SVG icon set (feather-style outlines) used across the sidebar and top bar. */
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
  menu: '<path d="M3.5 12h17M3.5 6h17M3.5 18h17"/>',
  search: '<circle cx="10.5" cy="10.5" r="7"/><path d="M20.5 20.5l-4.35-4.35"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.2 3.6-6.5 8-6.5s8 2.3 8 6.5"/>',
  warning:
    '<path d="M12 3.5 2.5 20.5h19z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.5" r="0.6" fill="currentColor" stroke="none"/>',
  refresh:
    '<path d="M4 12a8 8 0 0 1 14.3-4.9M20 12a8 8 0 0 1-14.3 4.9"/><path d="M18.5 3v4.5H14"/><path d="M5.5 21v-4.5H10"/>',
  download:
    '<path d="M12 3.5v11.5"/><path d="M7 10.5 12 15.5 17 10.5"/><path d="M4.5 17.5v2a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2"/>',
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
    v-html="ICONS[props.name] ?? ''"
  />
</template>
