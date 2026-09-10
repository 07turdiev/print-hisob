<script setup lang="ts">
import type { EmployeeStat } from '../api/types'
import AppIcon from './AppIcon.vue'

defineProps<{ employees: EmployeeStat[] }>()

const numberFormat = new Intl.NumberFormat('uz-UZ')
</script>

<template>
  <section v-if="employees.length" class="panel panel--warning">
    <header class="panel__head">
      <h2 class="panel__title">
        <span class="warn-icon"><AppIcon name="warning" :size="16" /></span>
        Noma'lum foydalanuvchilar
      </h2>
      <span class="panel__count">{{ employees.length }} ta login</span>
    </header>

    <div class="panel__body">
      <p class="hint">
        Ushbu login'lar AD (Active Directory) ro'yxatida topilmadi, lekin chop etish hodisalari
        qayd etilgan. Ularning varaqlari hisobdan chiqarilmaydi — kvota va bo'lim ma'lumotini
        tekshiring.
      </p>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-num">T/r</th>
            <th>Login</th>
            <th class="num">Sarflangan varaqlar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(emp, i) in employees" :key="emp.login">
            <td class="col-num">{{ i + 1 }}</td>
            <td class="strong">{{ emp.login }}</td>
            <td class="num">{{ numberFormat.format(emp.used) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.panel--warning {
  border-left: 3px solid var(--color-warning-fg);
}

.panel--warning .panel__head {
  background: var(--color-warning-bg);
  border-bottom-color: color-mix(in srgb, var(--color-warning-fg) 25%, transparent);
}

.panel--warning .panel__title {
  color: var(--color-warning-fg);
}

.warn-icon {
  display: inline-flex;
  color: var(--color-warning-fg);
}

.panel__body {
  padding-bottom: 0;
}

.hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  max-width: 80ch;
}
</style>
