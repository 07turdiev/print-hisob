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
    /** Sahifa sarlavhasi — sahifa boshidagi lentada ko'rsatiladi. */
    title: string
    /** Nonchalar (breadcrumb) uchun bo'lim nomi, yon menyu guruhiga mos keladi. */
    section?: string
    /** Sarlavha ostidagi qisqa izoh. */
    description?: string
    /** Kirish sahifasi token'siz ochiladi. */
    public?: boolean
    /** Sahifa uchun yil/davr tanlagichi ko'rsatiladimi. */
    showPeriodSelector?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { title: 'Kirish', public: true },
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: {
        title: "Umumiy ko'rinish",
        description: "Tanlangan davr bo'yicha qog'oz sarfining umumiy holati",
        showPeriodSelector: true,
      },
    },
    {
      path: '/choraklik',
      name: 'quarterly',
      component: QuarterlyView,
      meta: {
        title: 'Choraklik hisobot',
        section: 'Hisobotlar',
        description: "Chorak kesimida xodimlar bo'yicha sarf va kvota taqqoslamasi",
        showPeriodSelector: true,
      },
    },
    {
      path: '/oylik',
      name: 'monthly',
      component: MonthlyView,
      meta: {
        title: 'Oylik hisobot',
        section: 'Hisobotlar',
        description: "Oy kesimida xodimlar bo'yicha sarf va kvota taqqoslamasi",
        showPeriodSelector: true,
      },
    },
    {
      path: '/xodimlar',
      name: 'employees',
      component: EmployeesView,
      meta: {
        title: 'Xodimlar va kvotalar',
        section: "Ma'lumotnomalar",
        description: "Active Directory xodimlari ro'yxati va davr uchun qog'oz kvotalari",
        showPeriodSelector: true,
      },
    },
    {
      path: '/bolimlar',
      name: 'departments',
      component: DepartmentsView,
      meta: {
        title: "Bo'limlar",
        section: "Ma'lumotnomalar",
        description: "Bo'limlar kesimida jamlangan qog'oz sarfi",
        showPeriodSelector: true,
      },
    },
    {
      path: '/printerlar',
      name: 'printers',
      component: PrintersView,
      meta: {
        title: 'Printerlar',
        section: "Ma'lumotnomalar",
        description: "Qurilmalar bo'yicha sarf, xatolar va do'stona nomlar",
        showPeriodSelector: true,
      },
    },
    {
      path: '/jurnal',
      name: 'journal',
      component: JournalView,
      meta: {
        title: 'Chop etishlar jurnali',
        section: 'Nazorat',
        description: "Barcha chop etish hodisalarining batafsil ro'yxati",
        showPeriodSelector: false,
      },
    },
    {
      path: '/agentlar',
      name: 'agents',
      component: AgentsView,
      meta: {
        title: 'Agentlar holati',
        section: 'Nazorat',
        description: 'Ish stantsiyalaridagi hisobot agentlarining ishlash holati',
        showPeriodSelector: false,
      },
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

/** Brauzer yorlig'ida joriy sahifa nomi ko'rinib tursin. */
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — Printer Hisob` : 'Printer Hisob'
})

export default router
