<script setup lang="ts">
import { ref } from 'vue'
import { onClickOutside } from '../composables/useClickOutside'
import { useTheme } from '../composables/useTheme'
import { useAuthStore } from '../stores/auth'
import AppIcon from './AppIcon.vue'
import PeriodSelector from './PeriodSelector.vue'

defineProps<{ title: string; showPeriodSelector: boolean }>()
const emit = defineEmits<{ 'toggle-sidebar': [] }>()

const { theme, toggle: toggleTheme } = useTheme()
const auth = useAuthStore()

const menuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)
onClickOutside(menuRef, () => (menuOpen.value = false))

function logout() {
  auth.logout()
  window.location.href = '/login'
}
</script>

<template>
  <header class="top-bar">
    <button type="button" class="icon-btn menu-btn" title="Menyu" @click="emit('toggle-sidebar')">
      <AppIcon name="menu" :size="20" />
    </button>

    <h1 class="page-title">{{ title }}</h1>

    <div class="spacer" />

    <PeriodSelector v-if="showPeriodSelector" />

    <button type="button" class="icon-btn" :title="theme === 'dark' ? 'Yorug\' mavzu' : 'Qorong\'u mavzu'" @click="toggleTheme">
      <AppIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="18" />
    </button>

    <div class="user-menu" ref="menuRef">
      <button type="button" class="user-btn" @click="menuOpen = !menuOpen">
        <span class="avatar"><AppIcon name="user" :size="16" /></span>
        <span class="username">{{ auth.username ?? 'Foydalanuvchi' }}</span>
        <AppIcon name="chevron-down" :size="14" />
      </button>
      <div v-if="menuOpen" class="dropdown">
        <button type="button" class="dropdown-item" @click="logout">
          <AppIcon name="logout" :size="16" />
          <span>Chiqish</span>
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  position: sticky;
  top: 0;
  z-index: 10;
}

.page-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
  white-space: nowrap;
}

.spacer {
  flex: 1;
}

.menu-btn {
  display: none;
}

@media (max-width: 900px) {
  .menu-btn {
    display: inline-flex;
  }
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.15rem;
  height: 2.15rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.icon-btn:hover {
  background: var(--color-muted-bg);
  color: var(--color-text);
}

.user-menu {
  position: relative;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.85rem;
  font-weight: 600;
}

.user-btn:hover {
  background: var(--color-muted-bg);
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: var(--color-muted-bg);
  color: var(--color-text-muted);
}

.username {
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 0.4rem);
  min-width: 9rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: var(--shadow-card);
  padding: 0.3rem;
  z-index: 30;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.6rem;
  border: none;
  background: transparent;
  color: var(--color-danger-fg);
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 6px;
  text-align: left;
}

.dropdown-item:hover {
  background: var(--color-danger-bg);
}
</style>
