<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

defineProps<{ collapsed: boolean; mobileOpen: boolean }>()
const emit = defineEmits<{ 'toggle-collapsed': []; close: [] }>()

const NAV_ITEMS = [
  { to: '/', icon: 'home', label: 'Bosh sahifa' },
  { to: '/choraklik', icon: 'quarterly', label: 'Choraklik' },
  { to: '/oylik', icon: 'monthly', label: 'Oylik' },
  { to: '/xodimlar', icon: 'employees', label: 'Xodimlar' },
  { to: '/printerlar', icon: 'printers', label: 'Printerlar' },
  { to: '/bolimlar', icon: 'departments', label: "Bo'limlar" },
  { to: '/jurnal', icon: 'journal', label: "Jurnal" },
  { to: '/agentlar', icon: 'agents', label: 'Agentlar' },
]
</script>

<template>
  <aside class="sidebar" :class="{ collapsed, 'mobile-open': mobileOpen }">
    <div class="sidebar-header">
      <div class="brand-mark">PH</div>
      <span v-if="!collapsed" class="brand-title">Printer Hisob</span>
    </div>

    <nav class="nav">
      <RouterLink
        v-for="item in NAV_ITEMS"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        active-class="active"
        :title="collapsed ? item.label : ''"
        @click="emit('close')"
      >
        <AppIcon :name="item.icon" :size="19" />
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <button type="button" class="collapse-btn" @click="emit('toggle-collapsed')">
      <AppIcon :name="collapsed ? 'chevron-right' : 'chevron-left'" :size="16" />
      <span v-if="!collapsed">Yig'ish</span>
    </button>
  </aside>
  <div v-if="mobileOpen" class="sidebar-backdrop" @click="emit('close')" />
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: 15.5rem;
  flex-shrink: 0;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  height: 100vh;
  position: sticky;
  top: 0;
  transition: width 0.18s ease;
  z-index: 20;
}

.sidebar.collapsed {
  width: 4.25rem;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 1.1rem 1.1rem;
  border-bottom: 1px solid var(--color-border);
  min-height: 2.5rem;
}

.brand-mark {
  width: 2.15rem;
  height: 2.15rem;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: var(--brand-gradient);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.82rem;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
}

.brand-title {
  font-weight: 700;
  font-size: 1rem;
  white-space: nowrap;
  color: var(--color-text);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.75rem;
  flex: 1;
  overflow-y: auto;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.55rem 0.7rem;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.88rem;
  white-space: nowrap;
  transition: background-color var(--transition), color var(--transition);
}

.sidebar.collapsed .nav-item {
  justify-content: center;
}

.nav-item:hover {
  background: var(--color-accent-soft-bg);
  color: var(--color-text);
}

.nav-item.active {
  background: var(--color-accent-soft-bg);
  color: var(--color-accent-soft-fg);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: -0.75rem;
  top: 0.35rem;
  bottom: 0.35rem;
  width: 3px;
  border-radius: var(--radius-pill);
  background: var(--color-accent);
}

.sidebar.collapsed .nav-item.active::before {
  left: 0;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin: 0.75rem;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  transition: background-color var(--transition), color var(--transition);
}

.collapse-btn:hover {
  background: var(--color-accent-soft-bg);
  color: var(--color-accent-soft-fg);
}

.sidebar-backdrop {
  display: none;
}

@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    transform: translateX(-100%);
    box-shadow: var(--shadow-lg);
  }

  .sidebar.mobile-open {
    transform: translateX(0);
    width: 15.5rem;
  }

  .sidebar.collapsed:not(.mobile-open) {
    transform: translateX(-100%);
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.35);
    z-index: 19;
  }
}
</style>
