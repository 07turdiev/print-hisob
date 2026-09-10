<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/client'
import { useAuthStore } from '../stores/auth'
import AppIcon from '../components/AppIcon.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const FEATURES = [
  { icon: 'pages', text: "Xodimlar kesimida qog'oz sarfi va kvota nazorati" },
  { icon: 'quarterly', text: 'Choraklik va oylik hisobotlar, KPI shaklida eksport' },
  { icon: 'printers', text: "Printerlar va bo'limlar bo'yicha jamlanma tahlil" },
  { icon: 'shield', text: 'Active Directory bilan avtomatik sinxronizatsiya' },
]

async function submit() {
  if (!username.value || !password.value) return
  loading.value = true
  error.value = null
  try {
    await auth.login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      error.value = "Foydalanuvchi nomi yoki parol noto'g'ri"
    } else {
      error.value = 'Kirishda xatolik yuz berdi. Serverni tekshiring.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-layout">
      <!-- Chap taraf: tizim haqida qisqacha (tor ekranda yashiriladi) -->
      <aside class="intro">
        <div class="intro__brand">
          <span class="intro__mark"><AppIcon name="printers" :size="24" /></span>
          <div>
            <div class="intro__name">PRINTER HISOB</div>
            <div class="intro__sub">Qog'oz sarfini nazorat qilish tizimi</div>
          </div>
        </div>

        <ul class="intro__list">
          <li v-for="f in FEATURES" :key="f.text">
            <AppIcon :name="f.icon" :size="16" />
            <span>{{ f.text }}</span>
          </li>
        </ul>

        <p class="intro__foot">"MADANIY HAYOT MEDIA MARKETING MARKAZI" MCHJ ©</p>
      </aside>

      <!-- O'ng taraf: kirish shakli -->
      <form class="login-card" @submit.prevent="submit">
        <div class="login-card__head">
          <h1>Tizimga kirish</h1>
          <p>Tizimga faqat vakolatli xodimlar kirishi mumkin</p>
        </div>

        <label class="login-field">
          <span>Foydalanuvchi nomi</span>
          <input v-model="username" type="text" autocomplete="username" required autofocus />
        </label>

        <label class="login-field">
          <span>Parol</span>
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>

        <p v-if="error" class="alert alert--danger">
          <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
          <span>{{ error }}</span>
        </p>

        <button type="submit" class="btn btn-primary submit-btn" :disabled="loading">
          <AppIcon v-if="!loading" name="logout" :size="15" />
          {{ loading ? 'Tekshirilmoqda...' : 'Kirish' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background:
    radial-gradient(70% 60% at 12% 0%, rgba(15, 91, 168, 0.16), transparent 62%),
    radial-gradient(60% 55% at 92% 100%, rgba(15, 91, 168, 0.12), transparent 60%),
    var(--color-bg);
}

.login-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  width: 100%;
  max-width: 860px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  background: var(--color-surface);
}

/* Chap ko'k panel */
.intro {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-6) var(--space-5);
  background: var(--color-header-bg);
  color: var(--color-header-fg);
}

.intro__brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.intro__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.intro__name {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  color: #ffffff;
}

.intro__sub {
  font-size: var(--font-size-sm);
  color: var(--color-header-fg-muted);
}

.intro__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.intro__list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: var(--font-size-base);
  line-height: 1.45;
  color: #e2edf8;
}

.intro__list svg {
  flex-shrink: 0;
  margin-top: 1px;
  color: #9dc6ea;
}

.intro__foot {
  margin-top: auto;
  padding-top: var(--space-3);
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  font-size: var(--font-size-xs);
  color: var(--color-header-fg-muted);
}

/* O'ng shakl */
.login-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-6) var(--space-5);
  background: var(--color-surface);
}

.login-card__head h1 {
  font-size: 1.2rem;
  font-weight: 600;
}

.login-card__head p {
  margin-top: 4px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.login-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.login-field > span {
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.login-field input {
  height: 38px;
  font-size: var(--font-size-md);
}

.submit-btn {
  height: 38px;
  margin-top: var(--space-2);
  font-size: var(--font-size-md);
}

@media (max-width: 760px) {
  .login-layout {
    grid-template-columns: 1fr;
    max-width: 420px;
  }

  .intro {
    padding: var(--space-4);
    gap: var(--space-3);
  }

  .intro__list,
  .intro__foot {
    display: none;
  }
}
</style>
