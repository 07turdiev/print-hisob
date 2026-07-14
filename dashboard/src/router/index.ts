import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import HomeView from '../views/HomeView.vue'
import QuarterlyView from '../views/QuarterlyView.vue'
import MonthlyView from '../views/MonthlyView.vue'
import EmployeesView from '../views/EmployeesView.vue'
import PrintersView from '../views/PrintersView.vue'
import DepartmentsView from '../views/DepartmentsView.vue'
import JournalView from '../views/JournalView.vue'
import AgentsView from '../views/AgentsView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    /** Page title shown in the slim top bar. */
    title: string
    /** Login page is reachable without a token. */
    public?: boolean
    /** Whether the top bar's year/period selector applies to this page. */
    showPeriodSelector?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { title: 'Kirish', public: true } },
    { path: '/', name: 'home', component: HomeView, meta: { title: 'Bosh sahifa', showPeriodSelector: true } },
    {
      path: '/choraklik',
      name: 'quarterly',
      component: QuarterlyView,
      meta: { title: 'Choraklik hisobot', showPeriodSelector: true },
    },
    {
      path: '/oylik',
      name: 'monthly',
      component: MonthlyView,
      meta: { title: 'Oylik hisobot', showPeriodSelector: true },
    },
    {
      path: '/xodimlar',
      name: 'employees',
      component: EmployeesView,
      meta: { title: 'Xodimlar', showPeriodSelector: true },
    },
    {
      path: '/printerlar',
      name: 'printers',
      component: PrintersView,
      meta: { title: 'Printerlar', showPeriodSelector: true },
    },
    {
      path: '/bolimlar',
      name: 'departments',
      component: DepartmentsView,
      meta: { title: "Bo'limlar", showPeriodSelector: true },
    },
    {
      path: '/jurnal',
      name: 'journal',
      component: JournalView,
      meta: { title: "Chop etishlar jurnali", showPeriodSelector: false },
    },
    {
      path: '/agentlar',
      name: 'agents',
      component: AgentsView,
      meta: { title: 'Agentlar', showPeriodSelector: false },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : undefined }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { path: '/' }
  }
})

export default router
