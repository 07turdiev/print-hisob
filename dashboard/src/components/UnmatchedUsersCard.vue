<script setup lang="ts">
import type { EmployeeStat } from '../api/types'
import AppIcon from './AppIcon.vue'

defineProps<{ employees: EmployeeStat[] }>()
</script>

<template>
  <div v-if="employees.length" class="card warning-card">
    <h2><AppIcon name="warning" :size="17" class="warning-icon" /> Noma'lum foydalanuvchilar</h2>
    <p class="hint">
      Ushbu login'lar AD (Active Directory) ro'yxatida topilmadi, lekin chop etish
      hodisalari qayd etilgan. Ularning varaqlari yashirilmaydi — kvota va bo'lim
      ma'lumotini tekshiring.
    </p>
    <table>
      <thead>
        <tr>
          <th>Login</th>
          <th class="num">Sarflangan varaqlar</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="emp in employees" :key="emp.login">
          <td>{{ emp.login }}</td>
          <td class="num">{{ emp.used }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.warning-card {
  background: var(--color-warning-bg);
  border-color: transparent;
}

.warning-card h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--color-warning-fg);
  font-size: 1rem;
}

.warning-icon {
  flex-shrink: 0;
}

.warning-card :deep(table) {
  background: var(--color-surface);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.hint {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  margin: 0 0 0.75rem;
}

.num {
  text-align: right;
}
</style>
