<script setup lang="ts">
import { computed, ref } from 'vue'
import { onClickOutside } from '../composables/useClickOutside'
import { useTheme } from '../composables/useTheme'
import { useAuthStore } from '../stores/auth'
import AppIcon from './AppIcon.vue'

const emit = defineEmits<{ 'toggle-sidebar': [] }>()

const { theme, toggle: toggleTheme } = useTheme()
const auth = useAuthStore()

const menuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)
onClickOutside(menuRef, () => (menuOpen.value = false))

/** Foydalanuvchi nomining bosh harfi — avatar o'rnida ko'rsatiladi. */
const initial = computed(() => (auth.username ?? 'F').trim().charAt(0).toUpperCase())

const today = new Intl.DateTimeFormat('uz-UZ', {
  day: '2-digit',
  month: 'long',
  year: 'numeric',
}).format(new Date())

function logout() {
  auth.logout()
  window.location.href = '/login'
}
</script>

<template>
  <header class="top-bar">
    <button type="button" class="bar-btn menu-btn" title="Menyu" @click="emit('toggle-sidebar')">
      <AppIcon name="menu" :size="20" />
    </button>

    <div class="brand">
      <span class="brand-mark" aria-hidden="true">
        <AppIcon name="printers" :size="20" />
      </span>
      <span class="brand-text">
        <span class="brand-name">PRINTER HISOB</span>
        <span class="brand-sub">Qog'oz sarfini nazorat qilish tizimi</span>
      </span>
    </div>

    <div class="spacer" />

    <span class="today">
      <AppIcon name="monthly" :size="15" />
      {{ today }}
    </span>

    <button
      type="button"
      class="bar-btn"
      :title="theme === 'dark' ? 'Yorug\' mavzu' : 'Qorong\'u mavzu'"
      @click="toggleTheme"
    >
      <AppIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="17" />
    </button>

    <div ref="menuRef" class="user-menu">
      <button type="button" class="user-btn" @click="menuOpen = !menuOpen">
        <span class="avatar">{{ initial }}</span>
        <span class="user-text">
          <span class="user-name">{{ auth.username ?? 'Foydalanuvchi' }}</span>
          <span class="user-role">Administrator</span>
        </span>
        <AppIcon :name="menuOpen ? 'chevron-up' : 'chevron-down'" :size="14" />
      </button>

      <div v-if="menuOpen" class="dropdown">
        <div class="dropdown-head">
          <span class="dropdown-name">{{ auth.username ?? 'Foydalanuvchi' }}</span>
          <span class="dropdown-role">Tizim administratori</span>
        </div>
        <button type="button" class="dropdown-item" @click="logout">
          <AppIcon name="logout" :size="15" />
          <span>Tizimdan chiqish</span>
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 10px;
  height: var(--header-height);
  padding: 0 var(--space-4);
  background: var(--color-header-bg);
  border-bottom: 1px solid var(--color-header-border);
  color: var(--color-header-fg);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: #ffffff;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
}

.brand-name {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #ffffff;
}

.brand-sub {
  font-size: var(--font-size-xs);
  color: var(--color-header-fg-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.spacer {
  flex: 1;
}

.today {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--color-header-fg-muted);
  white-space: nowrap;
  padding-right: 6px;
  border-right: 1px solid rgba(255, 255, 255, 0.16);
  margin-right: 2px;
}

/* Ko'k lentadagi tugmalar — shaffof, hover'da yoritiladi */
.bar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-header-fg);
  transition: background-color var(--transition);
}

.bar-btn:hover {
  background: var(--color-header-hover);
}

.menu-btn {
  display: none;
}

.user-menu {
  position: relative;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 8px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.08);
  color: var(--color-header-fg);
  transition: background-color var(--transition);
}

.user-btn:hover {
  background: var(--color-header-hover);
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #ffffff;
  color: #0f5ba8;
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.user-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.15;
  min-width: 0;
}

.user-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: var(--font-size-xs);
  color: var(--color-header-fg-muted);
}

.dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 13rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-pop);
  padding: 4px;
  z-index: 40;
}

.dropdown-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 4px;
}

.dropdown-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.dropdown-role {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  border: none;
  background: transparent;
  color: var(--color-danger-fg);
  font-size: var(--font-size-base);
  font-weight: 600;
  border-radius: var(--radius-sm);
  text-align: left;
  transition: background-color var(--transition);
}

.dropdown-item:hover {
  background: var(--color-danger-bg);
}

@media (max-width: 960px) {
  .menu-btn {
    display: inline-flex;
  }

  .today,
  .user-text {
    display: none;
  }
}

@media (max-width: 560px) {
  .brand-sub {
    display: none;
  }
}
</style>
