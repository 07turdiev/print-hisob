<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import AppTopBar from './components/AppTopBar.vue'
import PageHeader from './components/PageHeader.vue'

const route = useRoute()
/** Kirish sahifasi karkassiz (sidebar/top bar'siz) ko'rsatiladi. */
const isChromeless = computed(() => route.meta.public === true)

const collapsed = ref(localStorage.getItem('printerhisob.sidebar-collapsed') === '1')
const mobileOpen = ref(false)

/** Tor ekranda yon panel "tortma" (drawer) bo'ladi, keng ekranda esa yig'iladi. */
const narrowQuery = window.matchMedia('(max-width: 960px)')
const isNarrow = ref(narrowQuery.matches)
const onNarrowChange = (e: MediaQueryListEvent) => {
  isNarrow.value = e.matches
  if (!e.matches) mobileOpen.value = false
}
narrowQuery.addEventListener('change', onNarrowChange)
onUnmounted(() => narrowQuery.removeEventListener('change', onNarrowChange))

/** Tortma rejimida menyu doim to'liq (yorliqlari bilan) ko'rsatiladi. */
const effectiveCollapsed = computed(() => collapsed.value && !isNarrow.value)

function toggleCollapsed() {
  collapsed.value = !collapsed.value
  localStorage.setItem('printerhisob.sidebar-collapsed', collapsed.value ? '1' : '0')
}

function toggleSidebar() {
  if (isNarrow.value) {
    mobileOpen.value = !mobileOpen.value
  } else {
    toggleCollapsed()
  }
}
</script>

<template>
  <RouterView v-if="isChromeless" />

  <div v-else class="app-shell">
    <AppTopBar @toggle-sidebar="toggleSidebar" />

    <div class="app-body">
      <AppSidebar
        :collapsed="effectiveCollapsed"
        :mobile-open="mobileOpen"
        @toggle-collapsed="toggleCollapsed"
        @close="mobileOpen = false"
      />

      <div class="app-main">
        <PageHeader
          :title="String(route.meta.title ?? '')"
          :section="route.meta.section"
          :description="route.meta.description"
          :show-period-selector="route.meta.showPeriodSelector === true"
        />
        <main class="app-content">
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-body {
  flex: 1;
  display: flex;
  align-items: flex-start;
  min-height: 0;
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
