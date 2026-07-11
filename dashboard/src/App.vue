<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import AppTopBar from './components/AppTopBar.vue'

const route = useRoute()
const isChromeless = computed(() => route.meta.public === true)

const collapsed = ref(localStorage.getItem('printerhisob.sidebar-collapsed') === '1')
const mobileOpen = ref(false)

function toggleCollapsed() {
  collapsed.value = !collapsed.value
  localStorage.setItem('printerhisob.sidebar-collapsed', collapsed.value ? '1' : '0')
}

function toggleSidebar() {
  // On narrow screens the sidebar is a drawer; on wide screens the button collapses it.
  if (window.innerWidth <= 900) {
    mobileOpen.value = !mobileOpen.value
  } else {
    toggleCollapsed()
  }
}
</script>

<template>
  <RouterView v-if="isChromeless" />
  <div v-else class="app-shell">
    <AppSidebar
      :collapsed="collapsed"
      :mobile-open="mobileOpen"
      @toggle-collapsed="toggleCollapsed"
      @close="mobileOpen = false"
    />
    <div class="app-main">
      <AppTopBar
        :title="String(route.meta.title ?? '')"
        :show-period-selector="route.meta.showPeriodSelector === true"
        @toggle-sidebar="toggleSidebar"
      />
      <main class="app-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
}

.app-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.app-content {
  flex: 1;
}
</style>
