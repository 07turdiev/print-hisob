<script setup lang="ts">
import { usePeriodStore } from '../stores/period'

defineProps<{
  departmentOptions: string[]
}>()

const store = usePeriodStore()
</script>

<template>
  <div class="department-filter card">
    <div class="group">
      <label>Bo'lim</label>
      <select :value="store.department" @change="store.setDepartment(($event.target as HTMLSelectElement).value)">
        <option value="">Barchasi</option>
        <option v-for="d in departmentOptions" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.department-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  padding: 0.85rem 1.25rem;
}

.group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

select {
  min-width: 9rem;
}
</style>
