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

      <button type="submit" class="submit-btn" :disabled="loading">
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
  background: var(--color-bg);
  padding: 1.5rem;
}

.login-card {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.brand-mark {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 8px;
  background: var(--color-accent);
  color: var(--color-accent-fg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.95rem;
}

.brand h1 {
  font-size: 1.15rem;
  margin: 0;
}

.subtitle {
  margin: -0.5rem 0 0;
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
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font-weight: 400;
  font-size: 0.95rem;
}

.field input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.submit-btn {
  padding: 0.65rem 1rem;
  border: none;
  border-radius: 8px;
  background: var(--color-accent);
  color: var(--color-accent-fg);
  font-weight: 700;
  font-size: 0.95rem;
}

.submit-btn:disabled {
  opacity: 0.65;
  cursor: default;
}

.error-banner {
  margin: 0;
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
}
</style>
