<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

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
    <form class="login-card card" @submit.prevent="submit">
      <div class="brand">
        <div class="brand-mark">PH</div>
        <h1>Printer Hisob</h1>
      </div>
      <p class="subtitle">Davom etish uchun tizimga kiring</p>

      <label class="field">
        <span>Foydalanuvchi</span>
        <input v-model="username" type="text" autocomplete="username" required autofocus />
      </label>

      <label class="field">
        <span>Parol</span>
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>

      <p v-if="error" class="error-banner">{{ error }}</p>

      <button type="submit" class="btn btn-primary submit-btn" :disabled="loading">
        {{ loading ? 'Tekshirilmoqda...' : 'Kirish' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(60% 55% at 15% 10%, rgba(99, 102, 241, 0.22), transparent 60%),
    radial-gradient(55% 50% at 88% 88%, rgba(139, 92, 246, 0.2), transparent 60%),
    var(--color-bg);
}

.login-card {
  position: relative;
  width: 100%;
  max-width: 380px;
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
  padding: 2.25rem 2rem;
  box-shadow: var(--shadow-lg);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand-mark {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: var(--radius);
  background: var(--brand-gradient);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
}

.brand h1 {
  font-size: 1.2rem;
  margin: 0;
  letter-spacing: -0.01em;
}

.subtitle {
  margin: -0.6rem 0 0;
  color: var(--color-text-muted);
  font-size: 0.88rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-muted);
}

.field input {
  font-weight: 400;
  font-size: 0.95rem;
}

.submit-btn {
  width: 100%;
  font-size: 0.95rem;
  margin-top: 0.25rem;
}

.error-banner {
  margin: 0;
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  padding: 0.55rem 0.8rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
}
</style>
