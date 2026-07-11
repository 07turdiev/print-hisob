import { defineStore } from 'pinia'
import { login as loginRequest } from '../api/client'

const TOKEN_KEY = 'printerhisob.token'
const USERNAME_KEY = 'printerhisob.username'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) as string | null,
    username: localStorage.getItem(USERNAME_KEY) as string | null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    /** Calls POST /api/auth/login and stores the returned token for subsequent requests. */
    async login(username: string, password: string) {
      const res = await loginRequest(username, password)
      this.token = res.accessToken
      this.username = username
      localStorage.setItem(TOKEN_KEY, res.accessToken)
      localStorage.setItem(USERNAME_KEY, username)
    },
    /** Clears the stored token. The router guard sends the user back to /login. */
    logout() {
      this.token = null
      this.username = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USERNAME_KEY)
    },
  },
})
