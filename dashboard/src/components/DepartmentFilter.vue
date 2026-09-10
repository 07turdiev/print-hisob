<script setup lang="ts">
import { usePeriodStore } from '../stores/period'

defineProps<{ departmentOptions: string[] }>()

const store = usePeriodStore()
</script>

<!-- Bo'lim bo'yicha filtr — filtr lentasi (.filter-bar) ichiga qo'yiladi. -->
<template>
  <label class="field">
    <span>Bo'lim</span>
    <select
      class="dept-select"
      :value="store.department"
      @change="store.setDepartment(($event.target as HTMLSelectElement).value)"
    >
      <option value="">Barcha bo'limlar</option>
      <option v-for="d in departmentOptions" :key="d" :value="d">{{ d }}</option>
    </select>
  </label>
</template>

<style scoped>
.dept-select {
  min-width: 16rem;
  max-width: 26rem;
}
</style>
