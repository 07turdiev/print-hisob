<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from './AppIcon.vue'
import PeriodSelector from './PeriodSelector.vue'

const props = defineProps<{
  title: string
  section?: string
  description?: string
  showPeriodSelector: boolean
}>()

const route = useRoute()
const isHome = computed(() => route.path === '/')

/** Nonchalar (breadcrumb): Bosh sahifa › bo'lim › joriy sahifa. */
const crumbs = computed(() => (props.section ? [props.section, props.title] : [props.title]))
</script>

<template>
  <div class="page-head">
    <div class="page-head__main">
      <nav class="crumbs" aria-label="Navigatsiya">
        <RouterLink to="/" class="crumb crumb--link">
          <AppIcon name="home" :size="13" />
          Bosh sahifa
        </RouterLink>
        <template v-if="!isHome">
          <template v-for="(crumb, i) in crumbs" :key="crumb">
            <span class="crumb-sep">/</span>
            <span class="crumb" :class="{ 'crumb--current': i === crumbs.length - 1 }">{{ crumb }}</span>
          </template>
        </template>
      </nav>

      <h1 class="page-title">{{ title }}</h1>
      <p v-if="description" class="page-desc">{{ description }}</p>
    </div>

    <div v-if="showPeriodSelector" class="page-head__aside">
      <span class="aside-label">Hisobot davri</span>
      <PeriodSelector />
    </div>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3) var(--space-4);
  padding: var(--space-3) var(--space-5);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.page-head__main {
  min-width: 0;
}

.crumbs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: 3px;
}

.crumb {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.crumb--link {
  color: var(--color-text-muted);
  text-decoration: none;
}

.crumb--link:hover {
  color: var(--color-accent);
  text-decoration: none;
}

.crumb--current {
  color: var(--color-text);
  font-weight: 600;
}

.crumb-sep {
  color: var(--color-border-strong);
}

.page-title {
  font-size: 1.15rem;
  font-weight: 600;
  line-height: 1.25;
}

.page-desc {
  margin-top: 2px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.page-head__aside {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.aside-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

@media (max-width: 700px) {
  .page-head {
    padding: var(--space-3);
  }
}
</style>
