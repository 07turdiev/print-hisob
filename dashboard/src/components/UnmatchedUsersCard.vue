<script setup lang="ts">
import type { EmployeeStat } from '../api/types'

defineProps<{ employees: EmployeeStat[] }>()
</script>

<template>
  <div v-if="employees.length" class="card warning-card">
    <h2>Noma'lum foydalanuvchilar</h2>
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
  border-color: var(--color-warning-fg);
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
