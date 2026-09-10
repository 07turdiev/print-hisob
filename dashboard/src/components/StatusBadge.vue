<script setup lang="ts">
import { computed } from 'vue'
import type { MatchStatus } from '../api/types'

const props = defineProps<{ status: MatchStatus }>()

/** AD bilan solishtirish holati: faol xodim, ketgan xodim yoki AD'da topilmagan login. */
const MAP: Record<string, { label: string; tone: string; title: string }> = {
  active: { label: 'Faol', tone: 'success', title: "AD'da mavjud va faol xodim" },
  inactive: { label: 'Ketgan', tone: 'muted', title: "AD'dan olib tashlangan xodim" },
  unmatched: { label: "Noma'lum", tone: 'warning', title: "Bu login AD ro'yxatida topilmadi" },
}

const info = computed(() => MAP[props.status] ?? { label: props.status, tone: 'muted', title: '' })
</script>

<template>
  <span class="badge" :class="`badge--${info.tone}`" :title="info.title">{{ info.label }}</span>
</template>
