<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

defineProps<{ collapsed: boolean; mobileOpen: boolean }>()
const emit = defineEmits<{ 'toggle-collapsed': []; close: [] }>()

/** Yon menyu bo'limlarga ajratilgan — davlat tizimlaridagi kabi guruhli ro'yxat. */
const NAV_GROUPS = [
  {
    label: 'Asosiy',
    items: [{ to: '/', icon: 'home', label: 'Bosh sahifa' }],
  },
  {
    label: 'Hisobotlar',
    items: [
      { to: '/choraklik', icon: 'quarterly', label: 'Choraklik hisobot' },
      { to: '/oylik', icon: 'monthly', label: 'Oylik hisobot' },
    ],
  },
  {
    label: "Ma'lumotnomalar",
    items: [
      { to: '/xodimlar', icon: 'employees', label: 'Xodimlar va kvotalar' },
      { to: '/bolimlar', icon: 'departments', label: "Bo'limlar" },
      { to: '/printerlar', icon: 'printers', label: 'Printerlar' },
    ],
  },
  {
    label: 'Nazorat',
    items: [
      { to: '/jurnal', icon: 'journal', label: 'Chop etishlar jurnali' },
      { to: '/agentlar', icon: 'agents', label: 'Agentlar holati' },
    ],
  },
]
</script>

<template>
  <aside class="sidebar" :class="{ collapsed, 'mobile-open': mobileOpen }">
    <nav class="nav">
      <div v-for="group in NAV_GROUPS" :key="group.label" class="nav-group">
        <span v-if="!collapsed" class="nav-group-label">{{ group.label }}</span>
        <span v-else class="nav-group-divider" />

        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="active"
          :title="collapsed ? item.label : ''"
          @click="emit('close')"
        >
          <AppIcon :name="item.icon" :size="18" />
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>

    <div class="sidebar-foot">
      <button
        type="button"
        class="collapse-btn"
        :title="collapsed ? 'Menyuni ochish' : 'Menyuni yig\'ish'"
        @click="emit('toggle-collapsed')"
      >
        <AppIcon :name="collapsed ? 'chevron-right' : 'chevron-left'" :size="15" />
        <span v-if="!collapsed">Menyuni yig'ish</span>
      </button>
    </div>
  </aside>

  <div v-if="mobileOpen" class="sidebar-backdrop" @click="emit('close')" />
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--color-sidebar-bg);
  border-right: 1px solid var(--color-border);
  position: sticky;
  top: var(--header-height);
  height: calc(100vh - var(--header-height));
  transition: width 0.16s ease;
  z-index: 20;
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

.nav {
  display: flex;
  flex-direction: column;
  padding: var(--space-2) 0;
  flex: 1;
  overflow-y: auto;
}

.nav-group {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--space-2);
}

.nav-group-label {
  padding: 10px 14px 4px;
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.nav-group-divider {
  height: 1px;
  margin: 6px 12px;
  background: var(--color-border);
}

/* Menyu bandi: faol bo'lganda chap chekkada ko'k chiziq paydo bo'ladi */
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  color: var(--color-text);
  text-decoration: none;
  font-size: var(--font-size-base);
  font-weight: 500;
  white-space: nowrap;
  border-left: 3px solid transparent;
  transition: background-color var(--transition), color var(--transition);
}

.nav-item:hover {
  background: var(--color-sidebar-hover);
  text-decoration: none;
}

.nav-item.active {
  background: var(--color-accent-soft-bg);
  border-left-color: var(--color-accent);
  color: var(--color-accent-soft-fg);
  font-weight: 600;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 9px 0;
  border-left-width: 0;
  border-right: 3px solid transparent;
}

.sidebar.collapsed .nav-item.active {
  border-right-color: var(--color-accent);
}

.sidebar-foot {
  border-top: 1px solid var(--color-border);
  padding: var(--space-2);
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 30px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 600;
  transition: background-color var(--transition), color var(--transition);
}

.collapse-btn:hover {
  background: var(--color-accent-soft-bg);
  border-color: var(--color-accent);
  color: var(--color-accent-soft-fg);
}

.sidebar-backdrop {
  display: none;
}

@media (max-width: 960px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: var(--header-height);
    transform: translateX(-100%);
    box-shadow: var(--shadow-lg);
    width: var(--sidebar-width);
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: var(--header-height) 0 0 0;
    background: rgba(10, 30, 55, 0.4);
    z-index: 19;
  }
}
</style>
